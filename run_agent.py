#!/usr/bin/env python3
"""
run_agent.py — textbook2skill Agent 模式入口

用法：
    python3 run_agent.py \
        --pdf /path/to/book.pdf \
        --skill-name financial-engineering \
        --book-title "金融工程 第4版" \
        --domain "金融工程" \
        --output /tmp/textbook2skill-agent-build \
        --prompts /path/to/textbook2skill/prompts \
        --llm-provider deepseek \
        [--ocr-cache /path/to/existing.md]

与原始 pipeline.py 的区别：
  - 不再按固定 8 步顺序执行，由 LLM Agent 自主决定每步策略
  - Agent 会先 analyze 教材结构，再用 plan_skills 自主决定抽取深度
  - 关键步骤后自动触发质量反思，质量差时会重试
  - 交付判断由 Agent 综合 benchmark 结果自主给出
"""
import argparse
import sys
from pathlib import Path

# 确保 skeleton/ 在 path 中（agent/__init__.py 也会做，但先在这里做更保险）
_here = Path(__file__).parent
sys.path.insert(0, str(_here / "skeleton"))

from llm import LLMClient
from agent.core import Agent


def main():
    p = argparse.ArgumentParser(
        description="textbook2skill Agent 模式（自主 Think→Act→Reflect 循环）"
    )
    p.add_argument("--pdf", type=Path, required=True,
                   help="PDF 教材绝对路径")
    p.add_argument("--skill-name", required=True,
                   help="skill 名（小写字母 + 连字符，如 financial-engineering）")
    p.add_argument("--book-title", required=True,
                   help="书名（用于 description 和 benchmark 出题）")
    p.add_argument("--domain", default="",
                   help="领域名（可选，如 金融工程、管理会计）")
    p.add_argument("--output", type=Path, required=True,
                   help="build 输出目录（会自动创建）")
    p.add_argument("--prompts", type=Path, required=True,
                   help="prompts/ 目录路径（含 extraction.md 等模板）")
    p.add_argument("--llm-provider", default="deepseek",
                   choices=["deepseek", "openai", "anthropic", "custom"],
                   help="LLM 提供商（默认 deepseek）")
    p.add_argument("--ocr-cache", type=Path, default=None,
                   help="已有 OCR markdown 路径，传入则跳过 OCR 步骤")
    args = p.parse_args()

    # 基本校验
    if not args.pdf.exists():
        print(f"❌ PDF 文件不存在: {args.pdf}", file=sys.stderr)
        sys.exit(1)
    if not args.prompts.exists():
        print(f"❌ prompts/ 目录不存在: {args.prompts}", file=sys.stderr)
        sys.exit(1)

    # 构造 LLM 客户端
    try:
        client = LLMClient.from_env(args.llm_provider)
    except Exception as e:
        print(f"❌ LLM 客户端初始化失败: {e}", file=sys.stderr)
        sys.exit(1)

    # 构造任务配置
    task = {
        "pdf_path": str(args.pdf.absolute()),
        "skill_name": args.skill_name,
        "book_title": args.book_title,
        "domain": args.domain,
        "ocr_cache": str(args.ocr_cache.absolute()) if args.ocr_cache else "",
    }

    # 启动 Agent
    agent = Agent(client, args.output, args.prompts)
    result = agent.run(task)

    # 输出最终结果
    print("\n" + "=" * 60)
    if result.get("deliverable"):
        print("✅  DELIVERABLE")
        print(f"   Skill 目录: {result.get('skill_dir', '')}")
        print(f"   摘要: {result.get('summary', '')}")
        print(f"\n   下一步: 复制到 ~/.claude/skills/{args.skill_name}/")
    else:
        print("⚠️   NOT DELIVERABLE")
        print(f"   原因: {result.get('reason', '')}")
        print(f"   Build 目录保留在: {args.output}（可检查 agent_state.json）")
    print("=" * 60)

    sys.exit(0 if result.get("deliverable") else 1)


if __name__ == "__main__":
    main()
