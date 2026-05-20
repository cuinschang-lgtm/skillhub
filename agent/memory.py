"""
Agent 工作记忆

跨循环保存 Agent 的感知状态、执行历史和反思结论。
to_context() 把摘要序列化为 LLM 可读的 JSON 字符串。
"""
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


@dataclass
class StepRecord:
    """单步执行的完整记录"""
    step: int
    tool_name: str
    tool_params: dict
    success: bool
    result_summary: str  # result JSON 截断到 400 字符
    reasoning: str = ""  # Agent 当时的推理


class AgentMemory:
    def __init__(self, task: dict, work_dir: Path):
        self.task = task          # 原始任务配置（pdf_path、skill_name 等）
        self.work_dir = work_dir
        self.steps: list[StepRecord] = []
        self.reflections: list[str] = []

        # Agent 的当前感知状态——会被各工具调用的结果逐步填充
        self.state: dict[str, Any] = {
            "phase": "init",          # init → probe → ocr → analyze → split
                                      # → plan → extract → quality_check
                                      # → assemble → benchmark → done
            "probe": None,            # probe 工具返回值
            "markdown_path": None,    # OCR 后的 markdown 文件路径
            "textbook_analysis": None,# analyze 工具返回值（结构概况）
            "chapters_summary": None, # split 后的章节摘要列表
            "chapters_file": None,    # chapters.json 路径
            "chapter_count": None,
            "skill_plan": None,       # plan_skills 工具输出（Agent 自主制定）
            "skill_plan_file": None,
            "extraction_result": None,
            "extracted_dir": None,
            "quality_eval": None,     # evaluate_quality 工具输出
            "skill_dir": None,
            "benchmark": None,
        }

    # ------------------------------------------------------------------ #
    #  写入                                                                 #
    # ------------------------------------------------------------------ #

    def add_step(
        self,
        tool_name: str,
        tool_params: dict,
        success: bool,
        result: Any,
        reasoning: str = "",
    ):
        summary = (
            json.dumps(result, ensure_ascii=False)[:400]
            if result is not None
            else "None"
        )
        self.steps.append(StepRecord(
            step=len(self.steps),
            tool_name=tool_name,
            tool_params=tool_params,
            success=success,
            result_summary=summary,
            reasoning=reasoning,
        ))

    def add_reflection(self, text: str):
        self.reflections.append(f"[step={len(self.steps)}] {text}")

    # ------------------------------------------------------------------ #
    #  给 LLM 的上下文序列化                                                #
    # ------------------------------------------------------------------ #

    def to_context(self) -> str:
        """序列化为 LLM 可理解的当前快照（控制 token 量）"""
        # 只保留非 None 的 state 字段；markdown_path 内容不放进来（太长）
        clean_state = {
            k: v for k, v in self.state.items()
            if v is not None and k not in ("markdown_path",)
        }

        # 最近 5 步执行历史
        recent = [
            {
                "step": r.step,
                "tool": r.tool_name,
                "success": r.success,
                "result": r.result_summary,
            }
            for r in self.steps[-5:]
        ]

        ctx = {
            "task": self.task,
            "current_phase": self.state["phase"],
            "state": clean_state,
            "recent_steps": recent,
            "reflections": self.reflections[-3:],
        }
        return json.dumps(ctx, ensure_ascii=False, indent=2)

    # ------------------------------------------------------------------ #
    #  持久化                                                               #
    # ------------------------------------------------------------------ #

    def save(self):
        self.work_dir.mkdir(parents=True, exist_ok=True)
        data = {
            "task": self.task,
            "state": {
                k: (str(v) if isinstance(v, Path) else v)
                for k, v in self.state.items()
            },
            "steps_count": len(self.steps),
            "reflections": self.reflections,
        }
        (self.work_dir / "agent_state.json").write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
