#!/usr/bin/env python3
"""chapter_quality_report.py — 切章质量分析（无 LLM 调用）

输入：build 目录（含 chapters.json + 可选 ocr-output.md）
输出：报告 dict / 命令行打印 + JSON 落盘

核心指标（codex P0 review 提的"必须有可观测性"）：
- chapter_count
- title_form_distribution: 章节标题形态分类
  - "正规章节"（第N章 / Chapter N / N\\.N\\s+TitleCase）
  - "mid-section"（（一）/ ①/ N\\.N\\.N / 案例xxx）
  - "appendix"（参考文献 / 习题答案 / 附录）
  - "uncategorized"
- size_stats: min / max / mean / median / std (chars)
- short_chapter_ratio: <3000 chars 的章数占比
- toc_match_rate: 如有 TOC，标题在 TOC 中的命中率
- duplicate_titles: 重复标题（如多个 "Solution"）
- split_strategy: 当前用的策略

用途：
1. 切章 patch 前后跑两次，对比指标变化
2. 识别哪些 build 切章质量低，需要重切
3. routing 上限上限估计（132 章 vs 11 章对路由难度天差地别）
"""
from __future__ import annotations

import json
import re
import statistics
import sys
from pathlib import Path

# ============ 标题形态分类 ============

CHAPTER_PATTERNS = [
    # 中文规范章节
    (re.compile(r"^第[一二三四五六七八九十百零\d]+章[\s　]"), "chapter-cn"),
    # 英文 Chapter
    (re.compile(r"^Chapter\s+\d+", re.IGNORECASE), "chapter-en"),
    # N.M Title (1.1 Introduction, 2.3 ...)
    (re.compile(r"^\d+\.\d+\s+[A-Z]"), "section-en"),
]

MID_SECTION_PATTERNS = [
    re.compile(r"^[（(][一二三四五六七八九十\d]+[）)]"),  # （一）（1）(1)
    re.compile(r"^[①②③④⑤⑥⑦⑧⑨⑩]"),  # ① ②
    re.compile(r"^\d+\.\d+\.\d+"),  # 7.6.4
    re.compile(r"^\d+、"),  # 1、
    re.compile(r"^[【\[]案例"),  # 【案例
    re.compile(r"^\$[①②③④]"),  # $① etc
    re.compile(r"^Solution\b", re.IGNORECASE),
    re.compile(r"^Problems?\b", re.IGNORECASE),
    re.compile(r"^EXAMPLE\s+\d+", re.IGNORECASE),
    re.compile(r"^Spreadsheet Exercises?", re.IGNORECASE),
    re.compile(r"^Case Study Exercises?", re.IGNORECASE),
]

APPENDIX_PATTERNS = [
    re.compile(r"参考文献|参考资料|References?\b", re.IGNORECASE),
    re.compile(r"习题答案|答案与提示|Answer Key", re.IGNORECASE),
    re.compile(r"^附录|^Appendix", re.IGNORECASE),
    re.compile(r"^索引|^Index\b", re.IGNORECASE),
    re.compile(r"^Selected\s+(References|Bibliography)", re.IGNORECASE),
    re.compile(r"^Pedagogy of This Book"),  # T3 教学引言
    re.compile(r"^Overview of the Book"),
]


def classify_title(title: str) -> str:
    """返回 chapter | mid-section | appendix | uncategorized"""
    title = title.strip().lstrip("# ").strip()
    for pattern in APPENDIX_PATTERNS:
        if pattern.search(title):
            return "appendix"
    for pattern, kind in CHAPTER_PATTERNS:
        if pattern.match(title):
            return f"chapter:{kind.split('-')[1]}"
    for pattern in MID_SECTION_PATTERNS:
        if pattern.match(title):
            return "mid-section"
    return "uncategorized"


# ============ 主分析 ============

def analyze_chapters(build_dir: Path) -> dict:
    chapters_json = build_dir / "chapters.json"
    if not chapters_json.exists():
        return {"error": f"missing {chapters_json}"}

    chapters = json.loads(chapters_json.read_text(encoding="utf-8"))
    n = len(chapters)
    sizes = [len(c.get("content", "")) for c in chapters]
    titles = [c.get("title", "") for c in chapters]

    classifications = [classify_title(t) for t in titles]
    title_form = {}
    for c in classifications:
        title_form[c] = title_form.get(c, 0) + 1

    short_count = sum(1 for s in sizes if s < 3000)
    very_short_count = sum(1 for s in sizes if s < 1000)
    huge_count = sum(1 for s in sizes if s > 80000)

    duplicate_titles = {}
    for t in titles:
        if titles.count(t) > 1:
            duplicate_titles[t] = titles.count(t)

    strategies = {}
    for c in chapters:
        s = c.get("source_strategy", "unknown")
        strategies[s] = strategies.get(s, 0) + 1

    # 标题"是否真章"判定（codex 的"chapter_quality"）
    real_chapter_count = sum(1 for c in classifications if c.startswith("chapter:"))
    mid_section_count = title_form.get("mid-section", 0)
    appendix_count = title_form.get("appendix", 0)
    uncategorized_count = title_form.get("uncategorized", 0)

    # 整体评级
    quality_score = compute_quality_score(
        n=n,
        real_chapter_count=real_chapter_count,
        mid_section_count=mid_section_count,
        short_count=short_count,
        duplicate_count=len(duplicate_titles),
    )

    report = {
        "build_dir": str(build_dir),
        "chapter_count": n,
        "split_strategies": strategies,
        "size_stats": {
            "min": min(sizes) if sizes else 0,
            "max": max(sizes) if sizes else 0,
            "mean": int(statistics.mean(sizes)) if sizes else 0,
            "median": int(statistics.median(sizes)) if sizes else 0,
            "stdev": int(statistics.stdev(sizes)) if len(sizes) > 1 else 0,
        },
        "title_form_distribution": title_form,
        "real_chapter_count": real_chapter_count,
        "real_chapter_ratio": round(real_chapter_count / n, 3) if n else 0,
        "mid_section_count": mid_section_count,
        "appendix_count": appendix_count,
        "uncategorized_count": uncategorized_count,
        "short_chapter_count": short_count,  # < 3000
        "very_short_count": very_short_count,  # < 1000
        "huge_chapter_count": huge_count,  # > 80000
        "duplicate_titles": duplicate_titles,
        "quality_score": quality_score,
        "verdict": verdict_for(quality_score, n, real_chapter_count, mid_section_count),
        "sample_titles": titles[:5] + (["..."] if len(titles) > 8 else []) + titles[-3:],
    }
    return report


def compute_quality_score(n: int, real_chapter_count: int, mid_section_count: int,
                          short_count: int, duplicate_count: int) -> int:
    """0-10 分。简单启发式，不是科学度量。"""
    score = 10
    # 章数离谱：< 3 或 > 30 扣分（典型教材 8-25 章）
    if n < 3:
        score -= 5
    elif n > 30:
        score -= min(5, (n - 30) // 20 + 2)  # 30+扣 2，50+扣 3，70+扣 4
    # 真章占比低
    real_ratio = real_chapter_count / n if n else 0
    if real_ratio < 0.5:
        score -= 3
    elif real_ratio < 0.8:
        score -= 1
    # mid-section 多
    if mid_section_count > 0:
        score -= min(3, mid_section_count // 3)
    # 重名多
    if duplicate_count > 2:
        score -= min(2, duplicate_count // 5 + 1)
    return max(0, score)


def verdict_for(score: int, n: int, real_chapter_count: int, mid_section_count: int) -> str:
    if score >= 8:
        return "good"
    if score >= 5:
        if n > 30:
            return "fair-too-fragmented"
        if mid_section_count > 0:
            return "fair-mid-section-leak"
        return "fair"
    if n > 50:
        return "poor-overfragmented"
    if real_chapter_count < n // 2:
        return "poor-mid-section-dominated"
    return "poor"


def format_report(rep: dict) -> str:
    lines = []
    lines.append(f"# Chapter Quality Report: {rep['build_dir']}")
    lines.append(f"\nVerdict: **{rep['verdict']}** (quality_score = {rep['quality_score']}/10)")
    lines.append(f"Chapter count: **{rep['chapter_count']}**")
    lines.append(f"Split strategies: {rep['split_strategies']}")
    lines.append(f"\n## Size stats (chars)")
    s = rep["size_stats"]
    lines.append(f"  min={s['min']} max={s['max']} mean={s['mean']} median={s['median']} stdev={s['stdev']}")
    lines.append(f"\n## Title form distribution")
    for k, v in sorted(rep["title_form_distribution"].items(), key=lambda x: -x[1]):
        lines.append(f"  {k}: {v}")
    lines.append(f"\n## 关键计数")
    lines.append(f"  真章节数 (chapter:cn/en/section): {rep['real_chapter_count']} / {rep['chapter_count']} = {rep['real_chapter_ratio']*100:.0f}%")
    lines.append(f"  mid-section 误判数: {rep['mid_section_count']}")
    lines.append(f"  附录章数: {rep['appendix_count']}")
    lines.append(f"  unclassified: {rep['uncategorized_count']}")
    lines.append(f"  短章 (<3000): {rep['short_chapter_count']}")
    lines.append(f"  极短章 (<1000): {rep['very_short_count']}")
    lines.append(f"  巨大章 (>80000): {rep['huge_chapter_count']}")
    if rep["duplicate_titles"]:
        lines.append(f"\n## 重复标题")
        for t, n in rep["duplicate_titles"].items():
            lines.append(f"  '{t}': {n} 次")
    lines.append(f"\n## Sample titles")
    for t in rep["sample_titles"]:
        lines.append(f"  {t}")
    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        sys.exit(f"Usage: {sys.argv[0]} <build_dir> [<out_json>]")
    build_dir = Path(sys.argv[1])
    rep = analyze_chapters(build_dir)
    if "error" in rep:
        sys.exit(rep["error"])
    print(format_report(rep))
    if len(sys.argv) >= 3:
        Path(sys.argv[2]).write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n[OK] written to {sys.argv[2]}")


if __name__ == "__main__":
    main()
