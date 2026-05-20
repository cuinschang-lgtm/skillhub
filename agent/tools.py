"""
Agent 工具集

把 skeleton/*.py 里的核心函数封装成 Agent 可调用的工具。
新增两个 Agent 专属工具：
  - analyze       : 分析教材全局结构（Agent 获得感知）
  - plan_skills   : 自主规划每章抽取深度 + 发现跨章主题（Agent 自主决策的核心）
  - evaluate_quality : 抽取后质量自检（Agent 反思闭环）
"""
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


# ------------------------------------------------------------------ #
#  基础数据结构                                                         #
# ------------------------------------------------------------------ #

@dataclass
class ToolResult:
    success: bool
    data: Any
    message: str


@dataclass
class Tool:
    name: str
    description: str
    params_schema: dict   # {param_name: "说明"}
    func: Callable


# ------------------------------------------------------------------ #
#  工具注册表                                                           #
# ------------------------------------------------------------------ #

class ToolRegistry:
    """
    持有所有工具的注册表。
    Agent 通过 execute(name, params) 调用，
    通过 list_descriptions() 获得工具说明（放进 system prompt）。
    """

    def __init__(self, llm_client, work_dir: Path, prompts_dir: Path):
        self.client = llm_client
        self.work_dir = work_dir
        self.prompts_dir = prompts_dir
        self._tools: dict[str, Tool] = {}
        self._register_all()

    # ------------------------------------------------------------------ #
    #  公开接口                                                             #
    # ------------------------------------------------------------------ #

    def execute(self, name: str, params: dict) -> ToolResult:
        tool = self._tools.get(name)
        if not tool:
            return ToolResult(False, None, f"未知工具: {name!r}，可用: {list(self._tools)}")
        try:
            data = tool.func(**params)
            return ToolResult(True, data, "ok")
        except Exception as e:
            return ToolResult(False, None, f"{type(e).__name__}: {e}")

    def list_descriptions(self) -> str:
        lines = []
        for t in self._tools.values():
            params = ", ".join(f"{k}: {v}" for k, v in t.params_schema.items())
            lines.append(f"- **{t.name}**({params})\n  {t.description}")
        return "\n".join(lines)

    # ------------------------------------------------------------------ #
    #  工具注册                                                             #
    # ------------------------------------------------------------------ #

    def _register_all(self):
        # 延迟导入 skeleton 模块（__init__.py 已经把 skeleton/ 加入 sys.path）
        from probe import probe_pdf
        from split import split_chapters
        from extract import extract_all
        from assemble import assemble
        from bench import gen_questions, run_benchmark
        from dataclasses import asdict

        work = self.work_dir
        client = self.client
        prompts = self.prompts_dir

        # ---- 1. probe ------------------------------------------------- #
        def tool_probe(pdf_path: str) -> dict:
            return probe_pdf(Path(pdf_path))

        # ---- 2. ocr --------------------------------------------------- #
        def tool_ocr(pdf_path: str, ocr_cache: str = "") -> dict:
            """提取文字层或调用 MinerU OCR，结果写到 ocr-output.md"""
            pdf = Path(pdf_path)
            out_md = work / "ocr-output.md"

            # 用已有缓存
            if ocr_cache and Path(ocr_cache).exists():
                text = Path(ocr_cache).read_text(encoding="utf-8")
                out_md.write_text(text, encoding="utf-8")
                return {"markdown_path": str(out_md), "chars": len(text), "source": "cache"}

            # 探测文字层（只看前 5 页）
            probe_text = subprocess.run(
                ["pdftotext", "-l", "5", str(pdf), "-"],
                capture_output=True, text=True,
            ).stdout
            has_text = len(probe_text.strip()) > 1000

            if has_text:
                book_md = work / "book.md"
                work.mkdir(parents=True, exist_ok=True)
                subprocess.run(["pdftotext", str(pdf), str(book_md)], check=True)
                text = book_md.read_text(encoding="utf-8")
                out_md.write_text(text, encoding="utf-8")
                return {"markdown_path": str(out_md), "chars": len(text), "source": "pdftotext"}
            else:
                from ocr_mineru import ocr_pdf, split_pdf_for_mineru
                parts = split_pdf_for_mineru(pdf, parts_dir=work / "ocr_parts")
                if len(parts) > 1:
                    print(f"[tool:ocr] PDF > 200 页，切 {len(parts)} 块", flush=True)
                    mds = [ocr_pdf(p, work / "ocr") for p in parts]
                    merged = work / "ocr" / "full-merged.md"
                    with merged.open("w", encoding="utf-8") as f:
                        for mp in mds:
                            f.write(mp.read_text(encoding="utf-8"))
                    text = merged.read_text(encoding="utf-8")
                else:
                    text = ocr_pdf(pdf, work / "ocr").read_text(encoding="utf-8")
                out_md.write_text(text, encoding="utf-8")
                return {"markdown_path": str(out_md), "chars": len(text), "source": "mineru"}

        # ---- 3. analyze（Agent 专属：感知教材全局结构）---------------- #
        def tool_analyze(markdown_path: str) -> dict:
            """
            读 OCR markdown，提取结构概况供 Agent 制定计划。
            不调用 LLM，纯规则提取，速度快。
            """
            md = Path(markdown_path).read_text(encoding="utf-8")
            preview = md[:2000]  # 前 2000 字让 Agent 感受写作风格
            h1s = re.findall(r"^#\s+(.+)$", md, re.MULTILINE)[:40]
            has_zh = bool(re.search(r"[一-鿿]", md[:500]))
            real_chapters = [
                t for t in h1s
                if re.match(r"^(第[一二三四五六七八九十百零\d]+章|Chapter\s+\d+)", t)
            ]
            return {
                "preview": preview,
                "all_h1_titles": h1s,
                "estimated_real_chapters": len(real_chapters),
                "total_chars": len(md),
                "language": "zh" if has_zh else "en",
                "avg_chars_per_chapter_estimate": len(md) // max(len(real_chapters), 1),
            }

        # ---- 4. split ------------------------------------------------- #
        def tool_split(markdown_path: str) -> dict:
            md = Path(markdown_path).read_text(encoding="utf-8")
            chapters = split_chapters(md, llm_client=client)
            chapters_json = [asdict(c) for c in chapters]
            out = work / "chapters.json"
            out.write_text(
                json.dumps(chapters_json, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            summary = [
                {
                    "idx": c["idx"],
                    "title": c["title"],
                    "chars": len(c["content"]),
                    "strategy": c["source_strategy"],
                }
                for c in chapters_json
            ]
            print(f"[tool:split] 识别 {len(chapters)} 章，策略: {chapters[0].source_strategy if chapters else 'N/A'}", flush=True)
            return {
                "chapters_count": len(chapters_json),
                "chapters_file": str(out),
                "summary": summary,
            }

        # ---- 5. plan_skills（Agent 专属：自主规划 skill 点）------------ #
        def tool_plan_skills(
            chapters_summary: list,
            book_title: str,
            domain: str = "",
        ) -> dict:
            """
            Agent 核心决策工具。
            LLM 分析所有章节摘要，决定：
            - 每章的抽取深度（full / brief / skip）
            - 是否存在跨章核心主题值得单独成为 skill
            - benchmark 出题量建议
            """
            prompt = f"""你是一位 skill 架构师，正在规划如何把《{book_title}》（{domain or "未知领域"}）编译成高质量领域知识 skill。

下面是所有章节的概况（idx、标题、字符数）：
{json.dumps(chapters_summary, ensure_ascii=False, indent=2)}

请自主分析并规划：
1. 每章的抽取深度：
   - full：核心内容章节，公式/案例/流程丰富，值得完整抽取
   - brief：内容较薄、或纯理论综述，只需简要抽取（内容会被截短至 8000 字）
   - skip：纯参考文献/索引/前言/习题答案等"非教学正文"，跳过
2. 跨章节的核心主题（如果有）：多个章节反复出现同一方法论/框架
3. 总体复杂度（high/medium/low）与建议 benchmark 题目数

输出严格合法 JSON（不要 markdown 代码块包裹）：
{{
  "chapter_plans": [
    {{"idx": 1, "title": "...", "mode": "full|brief|skip", "reason": "一句话理由"}}
  ],
  "cross_chapter_skills": [
    {{"theme": "主题名", "chapter_indices": [1, 3, 5], "description": "这个跨章主题是什么"}}
  ],
  "complexity": "high|medium|low",
  "recommended_questions": 30
}}"""
            resp = client.chat([{"role": "user", "content": prompt}])
            # 容错解析
            resp = resp.strip()
            if resp.startswith("```"):
                resp = re.sub(r"^```\w*\n?", "", resp)
                resp = re.sub(r"\n?```$", "", resp.strip())
            start, end = resp.find("{"), resp.rfind("}")
            if start >= 0 and end > start:
                resp = resp[start : end + 1]
            plan = json.loads(resp)

            plan_path = work / "skill_plan.json"
            plan_path.write_text(
                json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            full_count = sum(1 for p in plan.get("chapter_plans", []) if p.get("mode") == "full")
            brief_count = sum(1 for p in plan.get("chapter_plans", []) if p.get("mode") == "brief")
            skip_count = sum(1 for p in plan.get("chapter_plans", []) if p.get("mode") == "skip")
            print(
                f"[tool:plan_skills] full={full_count} brief={brief_count} skip={skip_count} "
                f"complexity={plan.get('complexity')} questions={plan.get('recommended_questions')}",
                flush=True,
            )
            return {**plan, "plan_file": str(plan_path)}

        # ---- 6. extract ----------------------------------------------- #
        def tool_extract(
            chapters_file: str,
            skill_plan_file: str = "",
            allow_partial: bool = True,
        ) -> dict:
            """
            按 Agent 制定的 plan 并发抽取章节。
            - skip 的章节直接过滤
            - brief 的章节 content 截短至 8000 字（触发 LLM 简要抽取）
            """
            chapters = json.loads(Path(chapters_file).read_text(encoding="utf-8"))

            if skill_plan_file and Path(skill_plan_file).exists():
                plan = json.loads(Path(skill_plan_file).read_text(encoding="utf-8"))
                mode_map = {
                    p["idx"]: p.get("mode", "full")
                    for p in plan.get("chapter_plans", [])
                }
                # 过滤 skip
                chapters = [c for c in chapters if mode_map.get(c["idx"], "full") != "skip"]
                # brief 模式截短内容
                for c in chapters:
                    if mode_map.get(c["idx"]) == "brief":
                        c["content"] = c["content"][:8000]

            extracted_dir = work / "extracted"
            results, manifest_path = extract_all(
                chapters, extracted_dir, client, prompts,
                allow_partial=allow_partial,
            )
            success_n = sum(1 for r in results if r.success)
            failed = [r.title for r in results if not r.success]
            print(f"[tool:extract] {success_n}/{len(results)} 章成功", flush=True)
            return {
                "success": success_n,
                "total": len(results),
                "failed_chapters": failed,
                "extracted_dir": str(extracted_dir),
                "manifest_file": str(manifest_path),
            }

        # ---- 7. evaluate_quality（Agent 专属：自检抽取质量）------------ #
        def tool_evaluate_quality(extracted_dir: str) -> dict:
            """
            规则检查每章抽取质量，给 Agent 提供反思依据。
            不调用 LLM，快速扫描结构性指标。
            """
            ed = Path(extracted_dir)
            md_files = [f for f in sorted(ed.glob("*.md")) if not f.name.startswith("_")]
            if not md_files:
                return {"quality_score": 0, "verdict": "poor", "issues": ["没有找到抽取文件"]}

            issues: list[str] = []
            chapter_scores: list[float] = []

            chapters_json_path = work / "chapters.json"
            chapters_data = {}
            if chapters_json_path.exists():
                for c in json.loads(chapters_json_path.read_text(encoding="utf-8")):
                    chapters_data[c["idx"]] = c

            for f in md_files:
                content = f.read_text(encoding="utf-8")
                score = 10.0

                if "[抽取失败" in content:
                    issues.append(f"{f.name}: 抽取失败")
                    chapter_scores.append(0.0)
                    continue

                # 缺关键结构 section
                if not re.search(r"^## 核心概念", content, re.MULTILINE):
                    score -= 3.0
                    issues.append(f"{f.name}: 缺 '## 核心概念'")

                # 核心概念条目数
                concepts = re.findall(r"^\s*-\s*\*\*[^*]+\*\*\s*[:：]", content, re.MULTILINE)
                if len(concepts) < 3:
                    score -= 2.0
                    issues.append(f"{f.name}: 核心概念太少 ({len(concepts)} 条)")

                # 开头不应是废话
                first_line = content.strip().split("\n", 1)[0]
                if not first_line.startswith("#"):
                    score -= 1.0
                    issues.append(f"{f.name}: 首行不是 '#' 标题")

                # 压缩比（原文 / 输出应在 3x~15x）
                idx_m = re.match(r"^(\d+)-", f.name)
                if idx_m and int(idx_m.group(1)) in chapters_data:
                    orig_len = len(chapters_data[int(idx_m.group(1))]["content"])
                    ratio = orig_len / max(len(content), 1)
                    if ratio < 2:
                        score -= 1.5
                        issues.append(f"{f.name}: 压缩比过低 ({ratio:.1f}x)，可能没有压缩")

                chapter_scores.append(max(0.0, score))

            avg = sum(chapter_scores) / len(chapter_scores) if chapter_scores else 0.0
            verdict = "good" if avg >= 7 else "needs_retry" if avg >= 4 else "poor"
            print(f"[tool:evaluate_quality] 平均分 {avg:.1f}/10，verdict={verdict}", flush=True)
            return {
                "quality_score": round(avg, 1),
                "chapters_checked": len(chapter_scores),
                "verdict": verdict,
                "issues": issues[:12],
            }

        # ---- 8. assemble ---------------------------------------------- #
        def tool_assemble(
            skill_name: str,
            book_title: str,
            domain: str = "",
            allow_partial: bool = True,
        ) -> dict:
            extracted_dir = work / "extracted"
            skill_dir = work / "skill"
            assemble(
                extracted_dir, skill_dir, skill_name, book_title,
                domain=domain, allow_partial=allow_partial,
            )
            chapter_count = len(list((skill_dir / "chapters").glob("*.md")))
            skill_md_size = len((skill_dir / "SKILL.md").read_text(encoding="utf-8"))
            print(f"[tool:assemble] skill_dir={skill_dir}，{chapter_count} 章，SKILL.md {skill_md_size} 字符", flush=True)
            return {
                "skill_dir": str(skill_dir),
                "chapter_count": chapter_count,
                "skill_md_chars": skill_md_size,
            }

        # ---- 9. benchmark --------------------------------------------- #
        def tool_benchmark(
            skill_dir: str,
            n_questions: int = 30,
            domain: str = "",
        ) -> dict:
            chapters_json_path = work / "chapters.json"
            if not chapters_json_path.exists():
                raise FileNotFoundError("chapters.json 不存在，需先运行 split")
            chapters = json.loads(chapters_json_path.read_text(encoding="utf-8"))

            # 按章节字数比例分配题目
            total_w = sum(len(c["content"]) for c in chapters)
            allocation: dict[str, int] = {}
            for c in chapters:
                prefix = f"{c['idx']:02d}-第{c['idx']}章"
                allocation[prefix] = max(1, round(n_questions * len(c["content"]) / total_w))
            # 调整到恰好 n_questions
            diff = n_questions - sum(allocation.values())
            if diff != 0:
                max_k = max(allocation, key=lambda k: allocation[k])
                allocation[max_k] = max(1, allocation[max_k] + diff)

            questions = gen_questions(
                chapters, allocation, client, prompts, domain=domain or "通用"
            )
            q_path = work / "benchmark-questions.json"
            q_path.write_text(
                json.dumps(questions, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            print(f"[tool:benchmark] 出题 {len(questions)} 道，开始评测...", flush=True)

            bench = run_benchmark(
                Path(skill_dir), questions, client, prompts,
                output_path=work / "benchmark.json",
            )
            results = bench["results"]
            n = len(results)
            with_ok = sum(1 for r in results if r["with_skill"].get("correct"))
            without_ok = sum(1 for r in results if r["without_skill"].get("correct"))
            delta = (with_ok - without_ok) / n * 100 if n > 0 else 0.0

            print(
                f"[tool:benchmark] WITH {with_ok/n*100:.1f}% / WITHOUT {without_ok/n*100:.1f}% / Δ {delta:+.1f}%",
                flush=True,
            )
            return {
                "total_questions": n,
                "with_pct": round(with_ok / n * 100, 1) if n else 0,
                "without_pct": round(without_ok / n * 100, 1) if n else 0,
                "delta_pct": round(delta, 1),
                "deliverable": delta >= 5.0,
                "report_file": str(work / "report.md"),
            }

        # ---- 注册 ----------------------------------------------------- #
        specs = [
            ("probe",
             "探测 PDF 元数据（页数、是否有文字层、语言、是否加密）",
             {"pdf_path": "PDF 文件绝对路径"},
             tool_probe),

            ("ocr",
             "提取 PDF 文字层（有文字层用 pdftotext；扫描版调 MinerU API）",
             {"pdf_path": "PDF 路径", "ocr_cache": "(可选) 已有 markdown 路径，传入则跳过 OCR"},
             tool_ocr),

            ("analyze",
             "分析 OCR markdown 的全局结构：标题列表、语言、总字数、估算章节数",
             {"markdown_path": "ocr-output.md 路径"},
             tool_analyze),

            ("split",
             "多策略章节切分（TOC-first → H1+size → 语义锚点 → LLM 兜底），输出 chapters.json",
             {"markdown_path": "ocr-output.md 路径"},
             tool_split),

            ("plan_skills",
             "【Agent 核心决策】分析章节摘要，自主规划每章抽取深度(full/brief/skip)和跨章主题",
             {"chapters_summary": "split 返回的 summary 列表",
              "book_title": "书名",
              "domain": "(可选) 领域名"},
             tool_plan_skills),

            ("extract",
             "按 plan 并发抽取章节知识，skip 的章节跳过，brief 的章节截短后抽取",
             {"chapters_file": "chapters.json 路径",
              "skill_plan_file": "(可选) skill_plan.json 路径",
              "allow_partial": "(可选) 是否允许部分失败继续，默认 True"},
             tool_extract),

            ("evaluate_quality",
             "【Agent 自检】检查抽取结果的结构完整性，给出质量评分和问题列表",
             {"extracted_dir": "extracted/ 目录路径"},
             tool_evaluate_quality),

            ("assemble",
             "把 extracted/*.md 组装成 skill 目录（SKILL.md + chapters/ + agents/openai.yaml）",
             {"skill_name": "skill 名（小写字母+连字符）",
              "book_title": "书名",
              "domain": "(可选) 领域名"},
             tool_assemble),

            ("benchmark",
             "出题 → WITH skill / WITHOUT skill 对比 → McNemar 统计 → 判断是否可交付",
             {"skill_dir": "skill/ 目录路径",
              "n_questions": "(可选) 题目数量，默认 30",
              "domain": "(可选) 领域名"},
             tool_benchmark),
        ]
        for name, desc, schema, func in specs:
            self._tools[name] = Tool(name, desc, schema, func)
