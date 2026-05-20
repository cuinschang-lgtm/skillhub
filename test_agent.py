"""
快速验证 Agent 核心逻辑（不需要 API key，不需要 requests/pyyaml）
运行：python3 test_agent.py
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "skeleton"))
import agent  # 触发 __init__.py
from agent.memory import AgentMemory
from agent.brain import AgentBrain, _SYSTEM_TEMPLATE
from agent.core import Agent

# ------------------------------------------------------------------ #
#  1. AgentMemory 基础功能
# ------------------------------------------------------------------ #
m = AgentMemory(
    {"pdf_path": "/tmp/book.pdf", "skill_name": "test", "book_title": "测试教材", "domain": "金融"},
    Path("/tmp/agent_test"),
)
m.state["phase"] = "analyzed"
m.state["chapter_count"] = 11
m.state["chapters_summary"] = [{"idx": 1, "title": "第1章 概论", "chars": 5000}]
m.add_step("analyze", {"markdown_path": "/tmp/ocr.md"}, True,
           {"language": "zh", "estimated_real_chapters": 11})
m.add_reflection("教材结构清晰，建议 full 抽取核心章节")

ctx = m.to_context()
parsed = json.loads(ctx)
assert parsed["current_phase"] == "analyzed", f"phase wrong: {parsed['current_phase']}"
assert len(parsed["recent_steps"]) == 1
assert parsed["recent_steps"][0]["tool"] == "analyze"
print("✓ AgentMemory 状态序列化正常")

# ------------------------------------------------------------------ #
#  2. AgentBrain：能正确解析带 markdown fence 的 LLM 输出
# ------------------------------------------------------------------ #
class FakeThinkClient:
    provider = "fake"
    def chat(self, messages, *, system=None):
        return (
            "```json\n"
            '{"action_type": "act", "observation": "已完成 split，11 章",'
            ' "reasoning": "应规划抽取深度", "action": {"tool": "plan_skills",'
            ' "params": {"chapters_summary": [], "book_title": "测试", "domain": "金融"}}}'
            "\n```"
        )

brain = AgentBrain(FakeThinkClient(), "- probe\n- plan_skills")
thought = brain.think(ctx)
assert thought["action_type"] == "act", f"expected act, got {thought['action_type']}"
assert thought["action"]["tool"] == "plan_skills"
print("✓ AgentBrain.think() 可正确解析 markdown fence JSON")

# ------------------------------------------------------------------ #
#  3. AgentBrain：reflect 路径
# ------------------------------------------------------------------ #
class FakeReflectClient:
    provider = "fake"
    def chat(self, messages, *, system=None):
        return (
            '{"action_type": "reflect", "observation": "抽取质量良好",'
            ' "quality_assessment": "8/10，结构完整", "decision": "continue",'
            ' "next_hint": "直接 assemble"}'
        )

brain2 = AgentBrain(FakeReflectClient(), "")
ref = brain2.reflect("extract", '{"success": 10, "total": 11}', "测试教材")
assert ref["action_type"] == "reflect"
assert ref["decision"] == "continue"
print("✓ AgentBrain.reflect() 解析正常")

# ------------------------------------------------------------------ #
#  4. AgentBrain：降级处理无效 JSON
# ------------------------------------------------------------------ #
class FakeBadJsonClient:
    provider = "fake"
    def chat(self, messages, *, system=None):
        return "这是无效的 JSON 响应，LLM 有时候会这样..."

brain3 = AgentBrain(FakeBadJsonClient(), "")
fallback = brain3.think("context")
assert fallback["action_type"] == "act"
assert fallback["action"]["tool"] == "__think_error__"
print("✓ AgentBrain 降级处理（无效 JSON）正常")

# ------------------------------------------------------------------ #
#  5. Agent._update_state 各阶段
# ------------------------------------------------------------------ #
m2 = AgentMemory({"book_title": "X"}, Path("/tmp"))
a = Agent.__new__(Agent)
a.work_dir = Path("/tmp")

a._update_state(m2, "probe", {"pages": 200, "needs_ocr": False, "language": "zh"})
assert m2.state["phase"] == "probe"
assert m2.state["probe"]["pages"] == 200

a._update_state(m2, "split", {"chapters_file": "/tmp/ch.json", "chapters_count": 8, "summary": []})
assert m2.state["phase"] == "split"
assert m2.state["chapter_count"] == 8
assert m2.state["chapters_file"] == "/tmp/ch.json"

a._update_state(m2, "plan_skills",
                {"chapter_plans": [{"idx": 1, "mode": "full"}],
                 "complexity": "medium", "plan_file": "/tmp/p.json"})
assert m2.state["phase"] == "planned"
assert "plan_file" not in m2.state["skill_plan"]  # plan_file 不应进入 skill_plan

a._update_state(m2, "extract",
                {"success": 7, "total": 8, "extracted_dir": "/tmp/extracted"})
assert m2.state["phase"] == "extracted"
assert m2.state["extracted_dir"] == "/tmp/extracted"

a._update_state(m2, "benchmark",
                {"delta_pct": 12.3, "deliverable": True, "with_pct": 86.7})
assert m2.state["phase"] == "benchmarked"
assert m2.state["benchmark"]["deliverable"] is True

print("✓ Agent._update_state() 所有阶段正常")

# ------------------------------------------------------------------ #
#  6. system prompt 构建
# ------------------------------------------------------------------ #
assert "__TOOLS_DESC__" in _SYSTEM_TEMPLATE
prompt = _SYSTEM_TEMPLATE.replace("__TOOLS_DESC__", "- probe\n- plan_skills")
assert "plan_skills" in prompt
assert "action_type" in prompt
print("✓ System prompt 构建正常")

# ------------------------------------------------------------------ #
print("\n========================================")
print("  所有核心逻辑测试通过 ✅")
print("========================================")
