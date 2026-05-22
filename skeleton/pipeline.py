from __future__ import annotations

"""端到端编排器（V1 修订版）

把 step 2-7 串起来。Step 1 (问用户) 和 Step 8 (安装) 是交互式的，不在这里跑。

V1 新增:
- A10: 每个 stage 写 state.json checkpoint，input_hash 一致就跳过
- A11: --skip-bench → --allow-unbenchmarked，跳过 bench 后强制输出 STATUS: NOT DELIVERABLE
- A12: 把 LLMClient 传给 split_chapters，让 LLM fallback 可用
- A6: 支持 --llm-provider {deepseek, openai, anthropic, custom}
- A9: 用新 extract_all 签名（返回 (results, manifest_path)）

用法:
    python3 pipeline.py \\
        --pdf /path/to/book.pdf \\
        --skill-name gao-cai \\
        --book-title "高级管理会计理论与实务" \\
        --domain "管理会计" \\
        --output /tmp/textbook2skill-build \\
        --prompts /path/to/textbook2skill/prompts \\
        --ocr-provider mineru \\
        --llm-provider deepseek \\
        [--ocr-cache <markdown_path>]   # 跳过 OCR 用现有 markdown
        [--resume]                       # 从 state.json 恢复，跳过已完成 stage
        [--from-stage extract]           # 强制从某 stage 重新开始
        [--allow-unbenchmarked]          # 跳过 benchmark（强制输出 NOT DELIVERABLE）

环境变量:
    MINERU_TOKEN  (扫描版 PDF 必需)
    DEEPSEEK_KEY / OPENAI_API_KEY / ANTHROPIC_API_KEY  (按所选 provider)
"""
import argparse
import hashlib
import json
import sys
from dataclasses import asdict
from pathlib import Path

from probe import probe_pdf
from split import split_chapters
from extract import extract_all
from assemble import assemble
from llm import LLMClient
from pdf_utils import write_text_layer_markdown


STAGES = ["probe", "ocr", "split", "extract", "assemble", "bench"]


# ---------- checkpoint helpers ----------

def _hash_input(s: str | bytes | Path) -> str:
    h = hashlib.sha256()
    if isinstance(s, Path):
        h.update(s.read_bytes())
    elif isinstance(s, str):
        h.update(s.encode("utf-8"))
    else:
        h.update(s)
    return h.hexdigest()[:16]


def load_state(work: Path) -> dict:
    f = work / "state.json"
    if not f.exists():
        return {"stages": {}}
    return json.loads(f.read_text(encoding="utf-8"))


def save_stage(work: Path, stage: str, *, status: str, input_hash: str, outputs: list[str], extra: dict | None = None) -> None:
    state = load_state(work)
    state["stages"][stage] = {
        "status": status,
        "input_hash": input_hash,
        "outputs": outputs,
        "extra": extra or {},
    }
    (work / "state.json").write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def stage_done(state: dict, stage: str, input_hash: str) -> bool:
    s = state.get("stages", {}).get(stage)
    return bool(s and s.get("status") == "ok" and s.get("input_hash") == input_hash)


# ---------- 主流程 ----------

def run_pipeline(args):
    work = args.output
    work.mkdir(parents=True, exist_ok=True)

    state = load_state(work) if args.resume else {"stages": {}}
    if args.from_stage and args.from_stage not in STAGES:
        raise ValueError(f"--from-stage 必须是 {STAGES} 之一")
    from_idx = STAGES.index(args.from_stage) if args.from_stage else 0

    # ---- Step 2: probe ----
    if STAGES.index("probe") >= from_idx:
        print("\n=== [2] PROBE ===", flush=True)
        pdf_hash = _hash_input(args.pdf)
        if args.resume and stage_done(state, "probe", pdf_hash):
            print(f"[probe] skipped (already done, hash={pdf_hash})", flush=True)
            probe = json.loads((work / "probe.json").read_text(encoding="utf-8"))
        else:
            probe = probe_pdf(args.pdf)
            (work / "probe.json").write_text(
                json.dumps(probe, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            save_stage(work, "probe", status="ok", input_hash=pdf_hash, outputs=["probe.json"])
        print(json.dumps(probe, indent=2, ensure_ascii=False))
    else:
        probe = json.loads((work / "probe.json").read_text(encoding="utf-8"))

    # ---- Step 3: OCR ----
    if STAGES.index("ocr") >= from_idx:
        print("\n=== [3] OCR ===", flush=True)
        if args.ocr_cache and args.ocr_cache.exists():
            print(f"使用 OCR 缓存: {args.ocr_cache}", flush=True)
            markdown_path = args.ocr_cache
            ocr_input_hash = _hash_input(markdown_path)
        else:
            ocr_input_hash = _hash_input(args.pdf) + ":" + args.ocr_provider
            cached_md = work / "ocr-output.md"
            if args.resume and stage_done(state, "ocr", ocr_input_hash) and cached_md.exists():
                print(f"[ocr] skipped (already done)", flush=True)
                markdown_path = cached_md
            elif probe["needs_ocr"]:
                if args.ocr_provider == "mineru":
                    from ocr_mineru import ocr_pdf, split_pdf_for_mineru
                    parts = split_pdf_for_mineru(args.pdf, parts_dir=work / "ocr_parts")
                    if len(parts) > 1:
                        print(f"PDF > 200 页，切成 {len(parts)} 块", flush=True)
                        md_paths = [ocr_pdf(p, work / "ocr") for p in parts]
                        markdown_path = work / "ocr" / "full-merged.md"
                        with markdown_path.open("w", encoding="utf-8") as f:
                            for mp in md_paths:
                                f.write(mp.read_text(encoding="utf-8"))
                    else:
                        markdown_path = ocr_pdf(args.pdf, work / "ocr")
                    # 拷贝到稳定路径用于 resume
                    cached_md.write_text(markdown_path.read_text(encoding="utf-8"), encoding="utf-8")
                    save_stage(work, "ocr", status="ok", input_hash=ocr_input_hash, outputs=["ocr-output.md"])
                else:
                    raise NotImplementedError(
                        f"OCR provider '{args.ocr_provider}' 未在 skeleton 实现。"
                        "扩展方式: 在 skeleton/ 加 ocr_<provider>.py"
                    )
            else:
                markdown_path = work / "book.md"
                write_text_layer_markdown(args.pdf, markdown_path)
                print(f"PDF 有文字层，pdftotext → {markdown_path}", flush=True)
                cached_md.write_text(markdown_path.read_text(encoding="utf-8"), encoding="utf-8")
                save_stage(work, "ocr", status="ok", input_hash=ocr_input_hash, outputs=["ocr-output.md"])

        markdown = markdown_path.read_text(encoding="utf-8")
        print(f"markdown 长度: {len(markdown)} 字符", flush=True)
    else:
        markdown_path = work / "ocr-output.md"
        markdown = markdown_path.read_text(encoding="utf-8")

    # ---- LLM client（split / extract / bench 共用）----
    client = LLMClient.from_env(args.llm_provider)

    # ---- Step 4: split ----
    if STAGES.index("split") >= from_idx:
        print("\n=== [4] SPLIT ===", flush=True)
        split_input_hash = _hash_input(markdown)
        if args.resume and stage_done(state, "split", split_input_hash):
            print(f"[split] skipped (already done)", flush=True)
            chapters_json = json.loads((work / "chapters.json").read_text(encoding="utf-8"))
        else:
            chapters = split_chapters(markdown, llm_client=client)
            chapters_json = [asdict(c) for c in chapters]
            (work / "chapters.json").write_text(
                json.dumps(chapters_json, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            print(f"识别 {len(chapters)} 章 (策略: {chapters[0].source_strategy if chapters else 'NA'})", flush=True)
            for c in chapters[:5]:
                print(f"  [{c.idx}] {c.title[:50]} ({len(c.content)} chars)", flush=True)
            if len(chapters) < 3:
                print("⚠️  章节数过少 (< 3)，建议 STOP 让用户检查 OCR 输出", flush=True)
                if not args.force:
                    save_stage(work, "split", status="too-few", input_hash=split_input_hash, outputs=["chapters.json"])
                    sys.exit(1)
            save_stage(work, "split", status="ok", input_hash=split_input_hash, outputs=["chapters.json"],
                       extra={"chapter_count": len(chapters_json)})
    else:
        chapters_json = json.loads((work / "chapters.json").read_text(encoding="utf-8"))

    # ---- Step 5: extract ----
    if STAGES.index("extract") >= from_idx:
        print("\n=== [5] EXTRACT ===", flush=True)
        extract_input_hash = _hash_input(json.dumps(chapters_json, ensure_ascii=False))
        extracted_dir = work / "extracted"
        if args.resume and stage_done(state, "extract", extract_input_hash):
            print(f"[extract] skipped (already done)", flush=True)
        else:
            try:
                results, manifest_path = extract_all(
                    chapters_json, extracted_dir, client, args.prompts,
                    allow_partial=args.allow_partial,
                )
                save_stage(work, "extract", status="ok", input_hash=extract_input_hash,
                           outputs=["extracted/", str(manifest_path.relative_to(work))],
                           extra={"success": sum(1 for r in results if r.success),
                                  "failed": sum(1 for r in results if not r.success)})
            except RuntimeError as e:
                save_stage(work, "extract", status="failed", input_hash=extract_input_hash, outputs=[])
                raise

    # ---- Step 6: assemble ----
    if STAGES.index("assemble") >= from_idx:
        print("\n=== [6] ASSEMBLE ===", flush=True)
        skill_dir = work / "skill"
        # assemble 输入是 extracted_dir 内容
        extracted_dir = work / "extracted"
        assemble_input_hash = _hash_input(json.dumps(
            sorted(p.name for p in extracted_dir.glob("*.md"))
        ))
        if args.resume and stage_done(state, "assemble", assemble_input_hash):
            print(f"[assemble] skipped (already done)", flush=True)
        else:
            assemble(
                extracted_dir, skill_dir, args.skill_name, args.book_title,
                domain=args.domain, allow_partial=args.allow_partial,
            )
            save_stage(work, "assemble", status="ok", input_hash=assemble_input_hash, outputs=["skill/"])
    else:
        skill_dir = work / "skill"

    # ---- Step 7: bench ----
    deliverable = True
    if args.allow_unbenchmarked:
        print("\n⚠️  跳过 benchmark — STATUS: NOT DELIVERABLE（没有 benchmark 不知道 skill 是否真有用）", flush=True)
        deliverable = False
    elif STAGES.index("bench") >= from_idx:
        print("\n=== [7] BENCHMARK ===", flush=True)
        bench_input_hash = _hash_input(json.dumps(chapters_json, ensure_ascii=False)) + ":" + args.skill_name
        if args.resume and stage_done(state, "bench", bench_input_hash) and (work / "benchmark.json").exists():
            print(f"[bench] skipped (already done)", flush=True)
        else:
            from bench import gen_questions, run_benchmark
            allocation = _allocate(chapters_json, total=30)
            print(f"题目分配: {allocation}", flush=True)
            questions = gen_questions(chapters_json, allocation, client, args.prompts, domain=args.domain or "通用")
            questions_path = work / "benchmark-questions.json"
            questions_path.write_text(json.dumps(questions, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"出题 {len(questions)} 道 → {questions_path}", flush=True)
            run_benchmark(skill_dir, questions, client, args.prompts,
                          output_path=work / "benchmark.json")
            save_stage(work, "bench", status="ok", input_hash=bench_input_hash,
                       outputs=["benchmark.json", "report.md", "benchmark-questions.json"])

    print("\n=== DONE ===", flush=True)
    if not deliverable:
        print("STATUS: NOT DELIVERABLE — 未跑 benchmark，install 步骤应阻止安装", flush=True)
    print(f"Skill 目录: {skill_dir}", flush=True)
    print(f"State: {work / 'state.json'}", flush=True)
    print(f"下一步: 复制到 ~/.claude/skills/{args.skill_name}/ (见 step 8)", flush=True)


def _allocate(chapters: list[dict], total: int = 30) -> dict[str, int]:
    """按章节 token 量比例分配题目数"""
    weights = [(c["idx"], len(c["content"])) for c in chapters]
    total_weight = sum(w for _, w in weights)
    allocation = {}
    for idx, w in weights:
        prefix = f"{idx:02d}-第{idx}章"
        n = max(1, round(total * w / total_weight))
        allocation[prefix] = n
    diff = total - sum(allocation.values())
    if diff != 0:
        max_key = max(allocation, key=lambda k: allocation[k])
        allocation[max_key] = max(1, allocation[max_key] + diff)
    return allocation


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--pdf", type=Path, required=True)
    p.add_argument("--skill-name", required=True)
    p.add_argument("--book-title", required=True)
    p.add_argument("--domain", default="", help="领域名（用于 bench 出题 prompt 和 description）")
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--prompts", type=Path, required=True,
                   help="textbook2skill/prompts/ 目录路径")
    p.add_argument("--ocr-provider", default="mineru")
    p.add_argument("--llm-provider", default="deepseek",
                   choices=["deepseek", "openai", "anthropic", "custom"])
    p.add_argument("--ocr-cache", type=Path, help="如已有 OCR markdown 文件，直接用，跳过 OCR")
    p.add_argument("--resume", action="store_true",
                   help="从 state.json 恢复，跳过已完成 stage（input_hash 一致）")
    p.add_argument("--from-stage", choices=STAGES,
                   help="强制从指定 stage 重新开始（覆盖 resume 的跳过逻辑）")
    p.add_argument("--allow-unbenchmarked", action="store_true",
                   help="跳过 benchmark（强制输出 NOT DELIVERABLE，不推荐）")
    p.add_argument("--allow-partial", action="store_true",
                   help="允许部分章节抽取失败 / 关键词缺失继续（不推荐）")
    p.add_argument("--force", action="store_true", help="即使 split 章节过少也继续")
    args = p.parse_args()
    run_pipeline(args)


if __name__ == "__main__":
    main()
