from __future__ import annotations

"""Benchmark runner（V1 修订版，必跑）

Input:  skill 目录 + LLM client + benchmark 出题数据
Output: benchmark.json + report.md

设计修订（V0 codex review 后 + V1 审计后）:
- 路由改 top-k：选 1-2 章 + confidence + reason
- 评分加 McNemar test 算 p-value（V1: exact binomial 替代 chi-square 近似，30 题小样本更稳）
- 加 Wilson 95% CI 算差距置信区间（DONE 模板承诺过）
- 分层指标：净胜题数 / 难度胜率 / 路由准确率 / 题型胜率
- 30 题降为 smoke test，结论必须含置信区间
- V1: prompt 加载只取 fenced block，不要把设计注释发给 LLM
- V1: 替换 {domain} 占位符
- V1: 用新 LLMError 分类

V0 实测:
- DeepSeek 31 题并发跑 ~30 秒
- WITH 90.3% vs WITHOUT 83.9% = +6.5% (但在噪声内)
- 第 2 章公式密集 +50% 是真信号
"""
import json
import math
import re
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from llm import LLMClient, LLMError


# ---------- prompt 加载（V1: 抽公共函数，只取 fenced block） ----------

def load_prompt_block(md_path: Path) -> str:
    """从 markdown 文件加载第一个 ``` fenced block 作为 prompt 模板。

    设计：prompt md 文件包含设计说明 + 实际 prompt（在 ``` 围栏里）。
    LLM 只应该看到围栏内的实际 prompt，不要被设计注释污染。
    """
    if not md_path.exists():
        raise FileNotFoundError(f"找不到 prompt 文件: {md_path}")
    raw = md_path.read_text(encoding="utf-8")
    m = re.search(r"```\s*\n(.+?)\n```", raw, re.DOTALL)
    if not m:
        raise ValueError(
            f"{md_path} 没有 fenced code block。prompt 模板必须包在 ``` 围栏里。"
        )
    return m.group(1)


# ---------- 出题 ----------

def gen_questions_one_chapter(
    client: LLMClient,
    prompt_template: str,
    chapter_prefix: str,
    title: str,
    content: str,
    count: int,
    domain: str = "通用",
) -> list[dict]:
    """单章出题"""
    if len(content) > 30000:
        content = content[:30000] + "\n[...章节后段省略...]"
    distribution = {1: "1 中等", 2: "1 简单 + 1 中等",
                    3: "1 简单 + 1 中等 + 1 困难",
                    4: "1 简单 + 2 中等 + 1 困难"}.get(count, f"按难度均衡 {count} 道")

    prompt = (prompt_template
              .replace("{count}", str(count))
              .replace("{distribution}", distribution)
              .replace("{chapter_prefix}", chapter_prefix)
              .replace("{domain}", domain)
              .replace("{chapter_text}", content))

    try:
        resp = client.chat([{"role": "user", "content": prompt}])
    except LLMError as e:
        print(f"[bench:gen] {chapter_prefix} 失败: {e}", flush=True)
        return []
    try:
        questions = _parse_json_array(resp)
    except json.JSONDecodeError as e:
        print(f"[bench:gen] {chapter_prefix} JSON 解析失败: {e}", flush=True)
        return []
    for q in questions:
        q["chapter"] = chapter_prefix
        q["chapter_title"] = title
    return questions


def gen_questions(
    chapters: list[dict],
    allocation: dict[str, int],
    client: LLMClient,
    prompt_dir: Path,
    domain: str = "通用",
    *,
    max_workers: int = 4,
) -> list[dict]:
    """按 allocation 并发出题"""
    prompt_template = load_prompt_block(prompt_dir / "question-gen.md")
    all_qs = []

    def worker(ch):
        prefix = f"{ch['idx']:02d}-第{ch['idx']}章"
        count = allocation.get(prefix, 0) or allocation.get(str(ch["idx"]), 0)
        if count == 0:
            return []
        return gen_questions_one_chapter(
            client, prompt_template, prefix, ch["title"], ch["content"], count, domain,
        )

    worker_count = max(1, min(max_workers, len(chapters)))
    with ThreadPoolExecutor(max_workers=worker_count) as ex:
        for qs in ex.map(worker, chapters):
            all_qs.extend(qs)
    return all_qs


def _parse_json_array(text: str) -> list:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
        if "```" in text:
            text = text.rsplit("```", 1)[0]
    start = text.find("[")
    end = text.rfind("]")
    if start >= 0 and end > start:
        text = text[start:end + 1]
    return json.loads(text)


# ---------- 跑题（WITH / WITHOUT skill）----------

def load_skill(skill_dir: Path) -> tuple[str, dict[str, str]]:
    skill_md = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    chapters = {f.name: f.read_text(encoding="utf-8")
                for f in sorted((skill_dir / "chapters").glob("*.md"))}
    return skill_md, chapters


def route_chapter_topk(
    client: LLMClient,
    prompt_template: str,
    question: dict,
    chapter_topics: dict[str, str],
    k: int = 2,
) -> list[str]:
    """路由：top-k 章节 + confidence。返回选中章节文件名列表"""
    topic_lines = "\n".join(f"- `{name}` — {topics}"
                             for name, topics in chapter_topics.items())
    prompt = (prompt_template
              .replace("{topic_lines}", topic_lines)
              .replace("{question}", question["question"])
              .replace("{topic}", question.get("topic", ""))
              .replace("{k}", str(k)))
    try:
        resp = client.chat([{"role": "user", "content": prompt}])
    except LLMError as e:
        print(f"[bench:route] 路由失败: {e}", flush=True)
        return []
    candidates = []
    for line in resp.strip().split("\n")[:k]:
        line = line.strip().strip("`").strip("- ").strip()
        if not line:
            continue
        if line in chapter_topics:
            candidates.append(line)
            continue
        for name in chapter_topics:
            if name in line or line.replace(".md", "") in name:
                candidates.append(name)
                break
    return candidates[:k] if candidates else []


def format_question(q: dict) -> str:
    if q["type"] == "choice":
        opts = "\n".join(f"  {k}. {v}" for k, v in q["options"].items())
        return f"【单选题】{q['question']}\n{opts}\n\n请回答（只输出 A/B/C/D）："
    return f"【填空题】{q['question']}\n\n请直接给出答案（一个词或一个数字）："


def answer_with_skill(client: LLMClient, q: dict, skill_dir: Path,
                       routing_prompt: str) -> dict:
    skill_md, chapters = load_skill(skill_dir)
    chapter_topics = _parse_chapter_topics(skill_md, list(chapters.keys()))
    selected = route_chapter_topk(client, routing_prompt, q, chapter_topics, k=2)
    chapter_content = "\n\n---\n\n".join(chapters.get(name, "") for name in selected)
    system = (
        "你是领域专家。下面是教材本章参考。回答用户题目时基于参考的口径、公式、术语，"
        "**主动展开** + 公式保留符号 + 维度全部列出。"
        "若参考章节不覆盖，明确说'本章未覆盖'后基于通用知识回答。\n\n"
        f"参考章节:\n====\n{chapter_content if chapter_content else '(未找到匹配章节)'}\n===="
    )
    answer = client.chat(
        [{"role": "user", "content": format_question(q)}],
        system=system,
    )
    return {"selected_chapters": selected, "raw_answer": answer}


def answer_without_skill(client: LLMClient, q: dict) -> dict:
    answer = client.chat(
        [{"role": "user", "content": format_question(q)}],
        system="你是领域专家。直接给答案。",
    )
    return {"raw_answer": answer}


def _parse_chapter_topics(skill_md: str, all_chapters: list[str]) -> dict[str, str]:
    topics = {}
    for line in skill_md.split("\n"):
        if not line.startswith("|") or "chapters/" not in line:
            continue
        parts = [p.strip() for p in line.strip("|").split("|")]
        if len(parts) >= 3:
            file_match = re.search(r"chapters/([\w\-_一-鿿\.]+)", parts[2])
            if file_match:
                fname = file_match.group(1).rstrip("`")
                if fname in all_chapters:
                    topics[fname] = parts[1]
    for name in all_chapters:
        if name not in topics:
            topics[name] = "(无关键词)"
    return topics


# ---------- 评分 ----------

def normalize_text(s: str) -> str:
    import unicodedata
    s = unicodedata.normalize("NFKC", s).strip().lower()
    s = re.sub(r"[\s\W]+", "", s)
    return s


def extract_mcq_letter(answer: str) -> str | None:
    """5 层 fallback 提取 MCQ"""
    raw = answer.strip()
    upper = raw.upper()
    if len(raw) <= 3:
        for c in upper:
            if c in "ABCD":
                return c
    tail = raw[-200:]
    patterns = [
        r"答案\s*[:：是为]\s*([ABCD])",
        r"应选\s*([ABCD])",
        r"选\s*([ABCD])\s*[项。]?",
        r"\b([ABCD])\s*[项。]?\s*(?:正确|对|是)",
        r"^\s*([ABCD])\s*[、.。]",
    ]
    for p in patterns:
        m = re.search(p, tail, re.MULTILINE | re.IGNORECASE)
        if m:
            return m.group(1).upper()
    for p in [r"\*\*\s*([ABCD])\s*\*\*", r"`\s*([ABCD])\s*`"]:
        m = re.search(p, raw)
        if m:
            return m.group(1).upper()
    matches = re.findall(r"(?<![A-Za-z])([ABCD])(?![A-Za-z])", upper)
    return matches[-1] if matches else None


def parse_number(s: str) -> float | None:
    s = s.replace(",", "").replace("，", "")
    m = re.search(r"-?\d+\.?\d*", s)
    if not m:
        return None
    val = float(m.group(0))
    if "%" in s or "％" in s:
        val = val / 100
    return val


def grade(q: dict, raw_answer: str) -> tuple[bool, str]:
    if q["type"] == "choice":
        letter = extract_mcq_letter(raw_answer)
        if letter is None:
            return False, "(无法提取)"
        return letter == q["answer"].strip().upper(), letter

    correct = q["answer"]
    aliases = [correct] + q.get("answer_aliases", [])
    raw_n = parse_number(raw_answer)
    correct_n = parse_number(correct)
    if raw_n is not None and correct_n is not None:
        if correct_n == 0:
            return abs(raw_n) < 0.001, str(raw_n)
        if abs(raw_n - correct_n) / abs(correct_n) <= 0.02:
            return True, str(raw_n)
    raw_norm = normalize_text(raw_answer)
    for a in aliases:
        if a and (normalize_text(a) in raw_norm or raw_norm in normalize_text(a)):
            return True, raw_answer.strip()[:50]
    return False, raw_answer.strip()[:50]


# ---------- 统计学（V1 修订）----------

def mcnemar_exact_p(b: int, c: int) -> float:
    """McNemar exact binomial test (two-sided p-value).
    b = WITH 对 + WITHOUT 错  数量
    c = WITH 错 + WITHOUT 对  数量
    H0: 两条件无差异 → discordant pairs 服从 Binomial(b+c, 0.5)
    """
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    # P(X <= k) under Binomial(n, 0.5), then * 2 for two-sided
    cum = sum(math.comb(n, i) for i in range(k + 1)) / (2 ** n)
    p = min(1.0, 2 * cum)
    return p


def wilson_ci(successes: int, total: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson 95% CI for a proportion."""
    if total == 0:
        return (0.0, 0.0)
    p = successes / total
    denom = 1 + z * z / total
    centre = p + z * z / (2 * total)
    spread = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total))
    lo = (centre - spread) / denom
    hi = (centre + spread) / denom
    return (max(0.0, lo), min(1.0, hi))


def newcombe_diff_ci(s1: int, n1: int, s2: int, n2: int, z: float = 1.96) -> tuple[float, float]:
    """Newcombe-Wilson 95% CI for difference of two independent proportions (s1/n1 - s2/n2).
    适用于独立样本（这里 WITH/WITHOUT 同题配对，严格不独立，但 30 题 smoke test 用作粗略 CI 可接受）"""
    p1 = s1 / n1 if n1 else 0.0
    p2 = s2 / n2 if n2 else 0.0
    l1, u1 = wilson_ci(s1, n1, z)
    l2, u2 = wilson_ci(s2, n2, z)
    delta = p1 - p2
    lo = delta - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2)
    hi = delta + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2)
    return (lo, hi)


# ---------- 主流程 ----------

def run_benchmark(
    skill_dir: Path,
    questions: list[dict],
    client: LLMClient,
    prompt_dir: Path,
    seed: int = 42,
    output_path: Path = Path("./benchmark.json"),
    *,
    max_workers: int = 6,
) -> dict:
    """跑 benchmark + 出报告"""
    import random
    random.seed(seed)
    routing_prompt = load_prompt_block(prompt_dir / "routing.md")

    def process(idx_q):
        idx, q = idx_q
        result = {**q}
        try:
            with_r = answer_with_skill(client, q, skill_dir, routing_prompt)
            with_correct, with_extracted = grade(q, with_r["raw_answer"])
            result["with_skill"] = {**with_r, "extracted": with_extracted, "correct": with_correct}
        except LLMError as e:
            result["with_skill"] = {"error": str(e), "error_kind": e.kind, "correct": False, "extracted": "(ERROR)"}
        try:
            without_r = answer_without_skill(client, q)
            without_correct, without_extracted = grade(q, without_r["raw_answer"])
            result["without_skill"] = {**without_r, "extracted": without_extracted, "correct": without_correct}
        except LLMError as e:
            result["without_skill"] = {"error": str(e), "error_kind": e.kind, "correct": False, "extracted": "(ERROR)"}
        result["correct_answer"] = q["answer"]
        return idx, result

    results = [None] * len(questions)
    worker_count = max(1, min(max_workers, len(questions)))
    with ThreadPoolExecutor(max_workers=worker_count) as ex:
        for idx, r in ex.map(process, [(i, q) for i, q in enumerate(questions)]):
            results[idx] = r

    output_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    report = build_report(results)
    print(report, flush=True)
    (output_path.parent / "report.md").write_text(report, encoding="utf-8")
    return {"results": results, "report": report}


def build_report(results: list[dict]) -> str:
    """生成 benchmark 报告（含 McNemar exact p-value + Wilson/Newcombe CI）"""
    n = len(results)
    wc = sum(1 for r in results if r["with_skill"].get("correct"))
    woc = sum(1 for r in results if r["without_skill"].get("correct"))

    b = sum(1 for r in results if r["with_skill"].get("correct") and not r["without_skill"].get("correct"))
    c = sum(1 for r in results if not r["with_skill"].get("correct") and r["without_skill"].get("correct"))
    p_value = mcnemar_exact_p(b, c)

    with_ci = wilson_ci(wc, n)
    without_ci = wilson_ci(woc, n)
    diff_ci = newcombe_diff_ci(wc, n, woc, n)

    lines = []
    lines.append("=" * 60)
    lines.append(f"Benchmark Report ({n} 题, smoke test)")
    lines.append("=" * 60)
    lines.append(f"WITH    skill: {wc}/{n} = {wc/n*100:.1f}%  95% CI [{with_ci[0]*100:.1f}%, {with_ci[1]*100:.1f}%]")
    lines.append(f"WITHOUT skill: {woc}/{n} = {woc/n*100:.1f}%  95% CI [{without_ci[0]*100:.1f}%, {without_ci[1]*100:.1f}%]")
    lines.append(f"差距 Δ: {(wc-woc)/n*100:+.1f}%  95% CI [{diff_ci[0]*100:+.1f}%, {diff_ci[1]*100:+.1f}%]")
    lines.append(f"McNemar exact (two-sided): b={b}, c={c}, p={p_value:.3f}")
    lines.append(f"显著性: {'p<0.05 ✓' if p_value < 0.05 else '不显著 (在噪声范围内)'}")
    lines.append("⚠️ 30 题为 smoke test，结论用于决定是否值得投入更大 eval；不做强结论")
    lines.append("")

    lines.append("=== 按难度 ===")
    for diff in ["easy", "medium", "hard"]:
        bucket = [r for r in results if r.get("difficulty") == diff]
        if not bucket:
            continue
        wc_b = sum(1 for r in bucket if r["with_skill"].get("correct"))
        woc_b = sum(1 for r in bucket if r["without_skill"].get("correct"))
        delta = (wc_b - woc_b) / len(bucket) * 100
        lines.append(f"  {diff:6}: WITH {wc_b}/{len(bucket)} | WITHOUT {woc_b}/{len(bucket)} | Δ {delta:+.0f}%")

    lines.append("")
    lines.append("=== 按章节 ===")
    chs = {}
    for r in results:
        chs.setdefault(r.get("chapter"), []).append(r)
    for ch, b_ in sorted(chs.items()):
        wc_b = sum(1 for r in b_ if r["with_skill"].get("correct"))
        woc_b = sum(1 for r in b_ if r["without_skill"].get("correct"))
        lines.append(f"  {ch}: WITH {wc_b}/{len(b_)} | WITHOUT {woc_b}/{len(b_)}")

    lines.append("")
    lines.append("=== 路由准确率 ===")
    correct_route = 0
    total_route = 0
    for r in results:
        expected = r.get("chapter")
        selected = r["with_skill"].get("selected_chapters", [])
        if not expected or not selected:
            continue
        total_route += 1
        if any(expected[:2] in s for s in selected):
            correct_route += 1
    if total_route > 0:
        lines.append(f"  {correct_route}/{total_route} = {correct_route/total_route*100:.0f}%")

    lines.append("")
    lines.append("=== 是否可交付 ===")
    delta = (wc - woc) / n * 100
    if p_value < 0.05 and delta >= 20:
        verdict = "强烈推荐 — skill 在这个领域价值大且统计显著"
    elif p_value < 0.05 and delta >= 10:
        verdict = "推荐 — skill 在多数场景能提升回答质量"
    elif p_value < 0.05 and delta >= 5:
        verdict = "有限提升 — skill 在难题/复杂场景有提升"
    elif delta > 0:
        verdict = "价值有限 — 差距不显著（可能是噪声），LLM baseline 已经强"
    elif delta == 0:
        verdict = "价值有限 — 与 baseline 持平，暂未证明 skill 带来额外收益"
    else:
        verdict = "不建议交付 — skill 反而拖累 LLM，需排查 prompt 或重做"
    lines.append(f"  {verdict}")

    return "\n".join(lines)


# 保留旧名字（向后兼容）
mcnemar_p_value = mcnemar_exact_p


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("skill_dir", type=Path)
    p.add_argument("questions_json", type=Path)
    p.add_argument("prompt_dir", type=Path)
    p.add_argument("provider", nargs="?", default="deepseek")
    args = p.parse_args()

    questions = json.loads(args.questions_json.read_text(encoding="utf-8"))
    client = LLMClient.from_env(args.provider)
    out = Path("./benchmark.json")
    run_benchmark(args.skill_dir, questions, client, args.prompt_dir, output_path=out)
