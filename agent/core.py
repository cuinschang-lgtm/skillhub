"""
Agent 主循环：Think → Act → Reflect

核心逻辑：
  1. brain.think(memory_context) 决定下一步工具调用
  2. registry.execute(tool, params)  执行工具
  3. 更新 memory.state
  4. 在关键步骤后主动调用 brain.reflect() 评估质量
  5. 根据反思结果决定 continue / retry / replan / stop
  6. 遇到 action_type=done 退出循环
"""
import json
from pathlib import Path
from typing import Any

from .memory import AgentMemory
from .tools import ToolRegistry
from .brain import AgentBrain

# 完成这些工具后主动触发反思
_REFLECT_AFTER = {"split", "extract", "evaluate_quality", "benchmark"}

# 最大迭代次数（防止 LLM 发散导致死循环）
MAX_ITER = 35


class Agent:
    def __init__(
        self,
        llm_client,
        work_dir: Path,
        prompts_dir: Path,
    ):
        self.work_dir = work_dir
        self.prompts_dir = prompts_dir
        self.registry = ToolRegistry(llm_client, work_dir, prompts_dir)
        self.brain = AgentBrain(llm_client, self.registry.list_descriptions())

    # ------------------------------------------------------------------ #
    #  主入口                                                               #
    # ------------------------------------------------------------------ #

    def run(self, task: dict) -> dict:
        """
        task 字段：
          pdf_path      : str  (必须)
          skill_name    : str  (必须)
          book_title    : str  (必须)
          domain        : str  (可选)
          ocr_cache     : str  (可选) 已有 OCR markdown 路径
        """
        memory = AgentMemory(task, self.work_dir)
        book_title = task.get("book_title", "Unknown")

        _header(f"Agent 启动：《{book_title}》")

        retry_count: dict[str, int] = {}  # tool_name → 已重试次数

        for iteration in range(1, MAX_ITER + 1):
            print(f"\n{'─'*50}", flush=True)
            print(f"  迭代 {iteration}/{MAX_ITER}  |  phase={memory.state['phase']}", flush=True)

            # ① THINK --------------------------------------------------- #
            thought = self.brain.think(memory.to_context())
            action_type = thought.get("action_type", "act")

            # ② DONE ----------------------------------------------------- #
            if action_type == "done":
                deliverable = thought.get("deliverable", False)
                summary = thought.get("summary", "")
                reason = thought.get("reason", "")
                skill_dir = thought.get("skill_dir", "")
                _header("Agent 完成")
                print(f"{'✅ 可交付' if deliverable else '⚠️  不建议交付'}", flush=True)
                print(f"原因: {reason}", flush=True)
                memory.save()
                return {
                    "done": True,
                    "deliverable": deliverable,
                    "summary": summary,
                    "skill_dir": skill_dir,
                    "reason": reason,
                }

            # ③ REFLECT（无工具调用，只记录）---------------------------- #
            if action_type == "reflect":
                observation = thought.get("observation", "")
                quality = thought.get("quality_assessment", "")
                decision = thought.get("decision", "continue")
                next_hint = thought.get("next_hint", "")
                print(f"🔍 反思 | {observation}", flush=True)
                print(f"   质量: {quality}  决策: {decision}", flush=True)
                if next_hint:
                    print(f"   建议: {next_hint}", flush=True)
                memory.add_reflection(f"{observation} → decision={decision}")
                if decision == "stop":
                    memory.save()
                    return {"done": True, "deliverable": False, "reason": observation}
                continue

            # ④ ACT ------------------------------------------------------ #
            action = thought.get("action", {})
            tool_name = action.get("tool", "")
            tool_params = action.get("params", {})
            observation = thought.get("observation", "")
            reasoning = thought.get("reasoning", "")

            print(f"💭 {observation[:120]}", flush=True)
            print(f"🧠 {reasoning[:150]}", flush=True)
            print(f"🔧 工具: {tool_name}  参数: {json.dumps(tool_params, ensure_ascii=False)[:200]}", flush=True)

            # 跳过解析错误
            if tool_name in ("__think_error__", "__reflect_error__", ""):
                print("[agent] 响应解析失败，跳过本轮", flush=True)
                continue

            result = self.registry.execute(tool_name, tool_params)

            if result.success:
                print(f"   ✓ {str(result.data)[:250]}", flush=True)
                self._update_state(memory, tool_name, result.data)
            else:
                print(f"   ✗ {result.message}", flush=True)

            memory.add_step(
                tool_name=tool_name,
                tool_params=tool_params,
                success=result.success,
                result=result.data if result.success else {"error": result.message},
                reasoning=reasoning,
            )

            # ⑤ 关键步骤后主动反思 --------------------------------------- #
            if tool_name in _REFLECT_AFTER and result.success:
                print(f"\n🔍 [{tool_name}] 完成，进行质量反思...", flush=True)
                reflection = self.brain.reflect(
                    tool_name=tool_name,
                    result_json=json.dumps(result.data, ensure_ascii=False),
                    book_title=book_title,
                )
                r_decision = reflection.get("decision", "continue")
                r_quality = reflection.get("quality_assessment", "")
                r_hint = reflection.get("next_hint", "")
                print(f"   质量: {r_quality}  决策: {r_decision}", flush=True)

                memory.add_reflection(
                    f"[{tool_name}] quality={r_quality} decision={r_decision} hint={r_hint}"
                )

                # retry 逻辑（最多重试 2 次）
                if r_decision == "retry":
                    retry_count[tool_name] = retry_count.get(tool_name, 0) + 1
                    if retry_count[tool_name] <= 2:
                        print(f"   ↩️  重试 {tool_name}（第 {retry_count[tool_name]} 次）", flush=True)
                        retry_result = self.registry.execute(tool_name, tool_params)
                        if retry_result.success:
                            self._update_state(memory, tool_name, retry_result.data)
                            memory.add_step(
                                tool_name=f"{tool_name}[retry]",
                                tool_params=tool_params,
                                success=True,
                                result=retry_result.data,
                                reasoning="自动重试",
                            )
                    else:
                        print(f"   ⚠️  {tool_name} 已重试 {retry_count[tool_name]-1} 次，继续", flush=True)

                elif r_decision == "stop":
                    memory.save()
                    return {
                        "done": True,
                        "deliverable": False,
                        "reason": reflection.get("observation", "质量不达标，Agent 停止"),
                    }

            memory.save()

        # 超出最大迭代次数
        print(f"\n⚠️  超出最大迭代次数 {MAX_ITER}", flush=True)
        return {"done": False, "deliverable": False, "reason": f"超出最大迭代次数 {MAX_ITER}"}

    # ------------------------------------------------------------------ #
    #  state 更新：工具结果 → memory.state                                  #
    # ------------------------------------------------------------------ #

    def _update_state(self, memory: AgentMemory, tool_name: str, data: Any):
        s = memory.state
        if tool_name == "probe":
            s["probe"] = data
            s["phase"] = "probe"

        elif tool_name == "ocr":
            s["markdown_path"] = data.get("markdown_path")
            s["phase"] = "ocr"

        elif tool_name == "analyze":
            s["textbook_analysis"] = {
                k: v for k, v in data.items() if k != "preview"
            }
            s["preview"] = data.get("preview", "")[:500]
            s["phase"] = "analyzed"

        elif tool_name == "split":
            s["chapters_file"] = data.get("chapters_file")
            s["chapter_count"] = data.get("chapters_count")
            s["chapters_summary"] = data.get("summary")
            s["phase"] = "split"

        elif tool_name == "plan_skills":
            s["skill_plan"] = {
                k: v for k, v in data.items() if k != "plan_file"
            }
            s["skill_plan_file"] = data.get("plan_file")
            s["phase"] = "planned"

        elif tool_name == "extract":
            s["extraction_result"] = data
            s["extracted_dir"] = data.get("extracted_dir")
            s["phase"] = "extracted"

        elif tool_name == "evaluate_quality":
            s["quality_eval"] = data
            # 不改变 phase，质量检查是可选中间步骤

        elif tool_name == "assemble":
            s["skill_dir"] = data.get("skill_dir")
            s["phase"] = "assembled"

        elif tool_name == "benchmark":
            s["benchmark"] = data
            s["phase"] = "benchmarked"


# ------------------------------------------------------------------ #
#  工具函数                                                             #
# ------------------------------------------------------------------ #

def _header(msg: str):
    bar = "=" * 60
    print(f"\n{bar}", flush=True)
    print(f"  {msg}", flush=True)
    print(f"{bar}", flush=True)
