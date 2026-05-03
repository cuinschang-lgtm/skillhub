"""组装最终 skill 目录（V1 修订版）

Input:  extracted/<idx>-<title>.md 文件们 + 元数据
Output: skill/{SKILL.md, chapters/*.md, agents/openai.yaml}

V1 修订（基于 V1 审计修复 B1/B2/B3/B4）:
- B2: frontmatter 用 yaml.safe_dump 生成，避免 `:`、引号、换行注入；name 严格校验
- B1: description 改 "pushy" 风格 + 关键词扩到 30+（按 1536 budget 截断）
- B3: 模板用 tool-neutral 表达（不绑定 "Claude" / "Read 工具"）
- B4: 关键词为空 raise，不再静默写 "(待补)"
- 跨 harness：同时输出 agents/openai.yaml 让 Codex 也能识别
"""
import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    raise ImportError(
        "需要 PyYAML。请安装: pip install pyyaml\n"
        "（用于安全生成 SKILL.md frontmatter，避免 YAML 注入）"
    )

# Anthropic 官方约束
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
NAME_MAX = 64
# description + when_to_use 在 skill listing 里被截到 1536 字符
DESC_BUDGET = 1500  # 留 36 字符给 frontmatter 边界


SKILL_MD_BODY_TEMPLATE = """# {book_title}

本 skill 由教材《{book_title}》自动炼化为 agent 可消费的领域知识包。**不是给学生看的学习指南，是给 agent 用来准确回答用户问题的领域参考。**

## 使用流程（必读）

1. 收到用户问题时，先看下方"章节速查表"，找最相关的 1-2 个章节
2. 加载对应的 `chapters/<filename>.md`（用所在 harness 的文件读取工具：Claude Code 用 Read，Codex 用 shell `cat`，等等）
3. 基于章节内容回答；若问题跨章，按相关性顺序最多加载 2 个
4. 章节文件结构：核心概念 / 公式与计算口径 / 方法流程 / 例题 / 易混点 / 关联
5. **回答时直接引用章节内容，不要说"根据参考资料"或"教材中提到"**

## 章节速查表

| 章节 | 关键词（精确命中） | 文件 |
|------|------|------|
{chapter_table}

## 反例

❌ 用户问 "X" → 把所有章节全加载（浪费 context）
❌ 用户问具体术语 → 不加载任何章节直接靠记忆（漏教材独有口径）
✅ 用户问 "X" → 只加载第 N 章（最相关那一章）
"""


CODEX_YAML_TEMPLATE = """# OpenAI Codex skill metadata（由 textbook2skill 自动生成）
# 与 Anthropic SKILL.md frontmatter 并列，让本 skill 跨 harness 可路由

name: {name}
description: |
{description_indented}

policy:
  allow_implicit_invocation: true
"""


def validate_name(name: str) -> None:
    """校验 skill name 符合 Anthropic 规范"""
    if not NAME_RE.match(name):
        raise ValueError(
            f"非法 skill name: {name!r}。"
            f"必须匹配 ^[a-z0-9]+(-[a-z0-9]+)*$ "
            f"（小写字母 / 数字 / 连字符；不能以连字符开头或结尾）"
        )
    if len(name) > NAME_MAX:
        raise ValueError(f"skill name 超过 {NAME_MAX} 字符: {name!r} ({len(name)} chars)")


def extract_keywords(chapter_md: str, max_kw: int = 12) -> list[str]:
    """从抽取后的章节 markdown 提关键词。
    源:
    - ## 核心概念 / ## Core Concepts 的 **术语**: 定义
    - ## 公式与计算口径 / ## Formulas 的 **公式名**:
    - ## 例题 / ## Examples 的 ### 例 X.M: topic / ### Example X.M:
    """
    kws = []

    # heading alias 表（中英都接受）
    concept_aliases = ["核心概念", "Core Concepts?", "Key Concepts?", "关键概念"]
    formula_aliases = ["公式与计算口径", "公式", "Formulas?", "Equations?"]
    example_aliases = ["例题", "Examples?", "Worked Examples?"]

    def grab_bullets(headings: list[str]) -> list[str]:
        out = []
        pattern = r"##\s*(?:" + "|".join(headings) + r")\s*\n(.+?)(?=\n##|\Z)"
        m = re.search(pattern, chapter_md, re.DOTALL | re.IGNORECASE)
        if not m:
            return out
        for line in m.group(1).split("\n"):
            km = re.match(r"^\s*-\s*\*\*([^*]+?)\*\*\s*[:：]", line)
            if km:
                out.append(km.group(1).strip())
        return out

    kws += grab_bullets(concept_aliases)
    kws += grab_bullets(formula_aliases)

    # 例题 topic
    ex_pattern = r"^###\s*(?:例|Example)[^:：\n]*[:：]\s*(.+)$"
    for m in re.finditer(ex_pattern, chapter_md, re.MULTILINE | re.IGNORECASE):
        topic = m.group(1).strip()
        if len(topic) > 24:
            topic = topic[:24]
        kws.append(topic)

    # 去重保序
    seen = set()
    unique = []
    for k in kws:
        if k and k not in seen:
            seen.add(k)
            unique.append(k)
    return unique[:max_kw]


def build_description(
    book_title: str,
    chapter_topics: list[str],
    all_keywords: list[str],
    domain: str = "",
) -> str:
    """构造 pushy description（合规于 Anthropic / Codex / Agent Skills open spec）

    Anthropic skill-creator 推荐：
    - 显式 trigger contexts
    - 包含同义词、缩略、相邻领域关键词
    - "pushy" 倾向：even if user doesn't explicitly mention it
    - 总长 ≤ 1500 字符（留给 frontmatter 边界）
    """
    domain_part = f"《{book_title}》" + (f"（{domain} 领域）" if domain else "")

    # 章节主题 + 全部关键词，按 budget 截断
    base = (
        f"{domain_part}专家技能，由教材原书自动炼化。"
        f"Use this skill **whenever** the user asks about anything covered by this textbook, "
        f"including 但不限于：{('、'.join(chapter_topics))}。"
        f"也要在用户用同义词、缩写、或问相邻概念时主动触发，覆盖关键词："
    )

    suffix_hint = "。优先使用本 skill 的章节速查表路由，再 load 对应 chapters/*.md。"
    budget_for_kws = DESC_BUDGET - len(base) - len(suffix_hint)

    kw_str_parts = []
    cur_len = 0
    for kw in all_keywords:
        added = (("、" if kw_str_parts else "") + kw)
        if cur_len + len(added) > budget_for_kws:
            break
        kw_str_parts.append(added)
        cur_len += len(added)

    kw_str = "".join(kw_str_parts) if kw_str_parts else "本书相关概念"
    description = base + kw_str + suffix_hint

    if len(description) > DESC_BUDGET:
        description = description[: DESC_BUDGET - 3] + "..."

    return description


def assemble(
    extracted_dir: Path,
    output_dir: Path,
    skill_name: str,
    book_title: str,
    domain: str = "",
    *,
    allow_partial: bool = False,
) -> Path:
    """组装最终 skill 目录

    Args:
        allow_partial: 默认 False。任何章节关键词为空时 fail-fast。
                       True 时允许，但仍会在 stderr 警告。
    """
    validate_name(skill_name)
    output_dir.mkdir(parents=True, exist_ok=True)
    chapters_dir = output_dir / "chapters"
    chapters_dir.mkdir(exist_ok=True)

    chapter_files = sorted(extracted_dir.glob("*.md"))
    if not chapter_files:
        raise RuntimeError(f"未找到抽取后的章节文件 in {extracted_dir}")

    chapter_rows = []
    chapter_topics = []
    all_keywords = []
    empty_chapters = []

    for src in chapter_files:
        content = src.read_text(encoding="utf-8")
        first = content.split("\n", 1)[0].lstrip("#").strip()
        topic_m = re.match(r"^第[^章]+章\s+(.+)$", first) or re.match(
            r"^Chapter\s+\d+[:：\s]+(.+)$", first, re.IGNORECASE
        )
        topic = topic_m.group(1) if topic_m else first
        chapter_topics.append(topic)

        keywords = extract_keywords(content)
        if not keywords:
            empty_chapters.append(src.name)
            keyword_str = "(关键词缺失)"
        else:
            all_keywords.extend(keywords)
            keyword_str = "、".join(keywords[:5])

        dest = chapters_dir / src.name
        dest.write_text(content, encoding="utf-8")
        chapter_rows.append(f"| {first} | {keyword_str} | `chapters/{src.name}` |")

    # B4: fail-fast on missing keywords
    if empty_chapters and not allow_partial:
        raise RuntimeError(
            f"以下章节关键词提取为空（共 {len(empty_chapters)} 章）：\n  - "
            + "\n  - ".join(empty_chapters)
            + "\n\n这通常意味着 LLM 抽取的章节没有 `## 核心概念` 等结构化 heading，"
            "或抽取本身失败 / 输出 [抽取失败] 占位。\n"
            "建议：1) 重跑 step 5 extract  "
            "2) 检查抽取 prompt 是否被正确加载  "
            "3) 如确认要带缺章交付，传 allow_partial=True（不推荐）。"
        )

    # B2: yaml.safe_dump 生成 frontmatter，杜绝注入
    description = build_description(book_title, chapter_topics, all_keywords, domain)
    frontmatter_dict = {
        "name": skill_name,
        "description": description,
    }
    frontmatter_yaml = yaml.safe_dump(
        frontmatter_dict,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
        width=100000,  # 不要在 description 中间换行
    )

    skill_md_body = SKILL_MD_BODY_TEMPLATE.format(
        book_title=book_title,
        chapter_table="\n".join(chapter_rows),
    )

    skill_md = f"---\n{frontmatter_yaml}---\n\n{skill_md_body}"
    skill_md_path = output_dir / "SKILL.md"
    skill_md_path.write_text(skill_md, encoding="utf-8")

    # 同时输出 agents/openai.yaml（跨 harness）
    agents_dir = output_dir / "agents"
    agents_dir.mkdir(exist_ok=True)
    desc_indented = "\n".join("  " + line for line in description.split("\n"))
    codex_yaml = CODEX_YAML_TEMPLATE.format(
        name=skill_name,
        description_indented=desc_indented,
    )
    (agents_dir / "openai.yaml").write_text(codex_yaml, encoding="utf-8")

    print(f"[assemble] {len(chapter_files)} 章 → {output_dir}", flush=True)
    print(f"[assemble] SKILL.md {len(skill_md)} 字符", flush=True)
    print(
        f"[assemble] description {len(description)} 字符 "
        f"(上限 {DESC_BUDGET}, 硬上限 1536)",
        flush=True,
    )
    if empty_chapters:
        print(
            f"[assemble] ⚠️ {len(empty_chapters)} 章关键词缺失 (allow_partial=True)",
            flush=True,
        )
    print(f"[assemble] 关键词样例: {all_keywords[:10]}", flush=True)
    print(f"[assemble] 跨 harness 元数据: agents/openai.yaml", flush=True)
    return output_dir


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("extracted_dir", type=Path)
    p.add_argument("output_dir", type=Path)
    p.add_argument("skill_name")
    p.add_argument("book_title")
    p.add_argument("--domain", default="", help="领域名（用于 description 描述）")
    p.add_argument("--allow-partial", action="store_true",
                   help="允许部分章节关键词缺失继续组装（不推荐）")
    args = p.parse_args()

    assemble(
        args.extracted_dir,
        args.output_dir,
        args.skill_name,
        args.book_title,
        domain=args.domain,
        allow_partial=args.allow_partial,
    )
