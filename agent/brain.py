"""
Agent 思考引擎

两个核心能力：
  think(context)   → 分析当前状态，决定下一步行动（返回结构化 JSON）
  reflect(...)     → 对工具执行结果做深度质量评估（返回结构化 JSON）

输出格式约定（Agent 必须遵守）：
  行动：  {"action_type": "act",     "observation": ..., "reasoning": ..., "action": {"tool": ..., "params": {...}}}
  反思：  {"action_type": "reflect", "observation": ..., "quality_assessment": ..., "decision": "continue|retry|replan", "next_hint": ...}
  完成：  {"action_type": "done",    "summary": ..., "deliverable": true/false, "reason": ..., "skill_dir": ...}
"""
import json
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from llm import LLMClient

# ------------------------------------------------------------------ #
#  System Prompt                                                        #
# ------------------------------------------------------------------ #
#  用字符串拼接而非 f-string，避免 JSON 示例里的 {} 需要双重转义
# ------------------------------------------------------------------ #

_SYSTEM_TEMPLATE = """\
你是一个专业的自主 AI Agent，目标是把 PDF 教材编译成高质量领域知识 skill。

【工作原则】
1. 先感知（probe → ocr → analyze），再规划（split → plan_skills），再执行（extract → evaluate_quality），最后交付（assemble → benchmark）
2. plan_skills 是你的核心决策步骤：基于章节结构，自主决定每章抽取深度（full/brief/skip）
3. evaluate_quality 后如果 verdict=needs_retry，优先重试 extract；verdict=poor 时考虑调整计划
4. benchmark 必须跑，delta_pct < 5 时标记 deliverable=false
5. 如果任务已经有 state 信息（phases 已完成），直接从当前阶段继续，不要重复已完成的步骤

【可用工具】
__TOOLS_DESC__

【输出格式——严格合法 JSON，不要 markdown 代码块包裹】

行动阶段（需要调用工具时）：
{
  "action_type": "act",
  "observation": "对当前状态和上一步结果的关键观察（1-2句）",
  "reasoning": "为什么选这个工具、预期得到什么（1-3句）",
  "action": {
    "tool": "工具名",
    "params": {"参数名": "参数值"}
  }
}

反思阶段（完成关键步骤后主动反思质量）：
{
  "action_type": "reflect",
  "observation": "结果的关键发现",
  "quality_assessment": "质量评价（1-10分及理由）",
  "decision": "continue|retry|replan",
  "next_hint": "下一步的最优路径建议"
}

完成阶段（所有步骤完成后）：
{
  "action_type": "done",
  "summary": "完成了什么",
  "deliverable": true,
  "reason": "可交付的理由（引用 benchmark delta）",
  "skill_dir": "skill 目录的绝对路径"
}
"""


# ------------------------------------------------------------------ #
#  AgentBrain                                                          #
# ------------------------------------------------------------------ #

class AgentBrain:
    def __init__(self, llm_client: "LLMClient", tools_description: str):
        self.client = llm_client
        self.system = _SYSTEM_TEMPLATE.replace("__TOOLS_DESC__", tools_description)

    def think(self, memory_context: str) -> dict:
        """
        基于当前记忆快照，让 LLM 决定下一步行动。
        返回解析后的 dict，失败时降级为 {"action_type": "act", ...error...}
        """
        user_msg = (
            "当前任务状态如下，请分析并决定下一步行动。\n\n"
            f"```json\n{memory_context}\n```\n\n"
            "输出严格合法 JSON（不要 markdown 代码块包裹）："
        )
        raw = self.client.chat(
            [{"role": "user", "content": user_msg}],
            system=self.system,
        )
        return self._parse(raw, fallback_tool="__think_error__")

    def reflect(self, tool_name: str, result_json: str, book_title: str) -> dict:
        """
        对某工具的执行结果做质量反思。
        返回 reflect 格式 dict。
        """
        user_msg = (
            f"你刚刚完成了工具 **{tool_name}** 的调用，目标是编译《{book_title}》。\n\n"
            f"工具结果摘要：\n```json\n{result_json[:800]}\n```\n\n"
            "请做质量反思，输出 reflect 格式 JSON："
        )
        raw = self.client.chat(
            [{"role": "user", "content": user_msg}],
            system=self.system,
        )
        parsed = self._parse(raw, fallback_tool="__reflect_error__")
        # 保证 action_type 是 reflect
        if parsed.get("action_type") != "reflect":
            parsed["action_type"] = "reflect"
            parsed.setdefault("decision", "continue")
        return parsed

    # ------------------------------------------------------------------ #
    #  内部：JSON 解析 + 降级处理                                           #
    # ------------------------------------------------------------------ #

    def _parse(self, text: str, fallback_tool: str) -> dict:
        text = text.strip()

        # 剥除可能的 ```json ... ``` 包裹
        if text.startswith("```"):
            text = re.sub(r"^```\w*\n?", "", text)
            text = re.sub(r"\n?```$", "", text.strip())

        # 找第一个 { 到最后一个 }
        start, end = text.find("{"), text.rfind("}")
        if start >= 0 and end > start:
            text = text[start : end + 1]

        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            print(f"[brain] JSON 解析失败: {e}", flush=True)
            print(f"[brain] 原始响应前 300 字: {text[:300]}", flush=True)
            return {
                "action_type": "act",
                "observation": "LLM 响应解析失败，降级跳过",
                "reasoning": "parse_error",
                "action": {"tool": fallback_tool, "params": {}},
            }
