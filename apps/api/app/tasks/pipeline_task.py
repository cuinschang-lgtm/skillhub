"""Pipeline background task — runs the textbook pipeline in demo mode."""

import json
import os
import sys
import traceback
import uuid
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.config import normalize_database_url, settings
from app.models import BenchmarkResult, Skill, Task
from app.tasks.celery_app import celery_app
from app.ws.bus import progress_bus

def _resolve_support_dir(name: str) -> Path:
    env_name = f"SKILLHUB_{name.upper()}_DIR"
    candidates: list[Path] = []

    env_value = os.environ.get(env_name)
    if env_value:
        candidates.append(Path(env_value))

    file_path = Path(__file__).resolve()
    candidates.extend(parent / name for parent in file_path.parents)
    candidates.append(Path.cwd() / name)

    seen: set[Path] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        if candidate.exists():
            return candidate

    searched = ", ".join(str(path) for path in seen)
    raise RuntimeError(f"Unable to locate {name} directory. Checked: {searched}")


SKELETON_DIR = _resolve_support_dir("skeleton")
PROMPTS_DIR = _resolve_support_dir("prompts")
if str(SKELETON_DIR) not in sys.path:
    sys.path.insert(0, str(SKELETON_DIR))

from probe import probe_pdf
from split import split_chapters
from extract import extract_all
from assemble import assemble
from llm import LLMClient
from bench import build_report, gen_questions, run_benchmark, mcnemar_exact_p, newcombe_diff_ci
from ocr_mineru import ocr_pdf, split_pdf_for_mineru
from pipeline import _allocate
from pdf_utils import summarize_markdown_text, write_text_layer_markdown


def publish_progress(task_id: str, stage: str, status: str, message: str = "", progress: int = 0, extra: dict = None):
    payload = {
        "stage": stage,
        "status": status,
        "message": message,
        "progress": progress,
        "extra": extra or {},
    }
    progress_bus.publish(task_id, json.dumps(payload, ensure_ascii=False))


SYNC_DATABASE_URL = normalize_database_url(settings.database_url, async_mode=False)
sync_engine = create_engine(SYNC_DATABASE_URL, future=True)


def _update_task(task_uuid: uuid.UUID, **fields) -> Task:
    with Session(sync_engine) as db:
        task = db.get(Task, task_uuid)
        if not task:
            raise RuntimeError(f"Task not found: {task_uuid}")
        for key, value in fields.items():
            setattr(task, key, value)
        db.commit()
        db.refresh(task)
        return task


def _load_task(task_uuid: uuid.UUID) -> Task:
    with Session(sync_engine) as db:
        task = db.get(Task, task_uuid)
        if not task:
            raise RuntimeError(f"Task not found: {task_uuid}")
        db.expunge(task)
        return task


def _set_default_api_keys() -> None:
    deepseek_key = settings.deepseek_key or os.environ.get("DEEPSEEK_API_KEY", "")
    if deepseek_key and not os.environ.get("DEEPSEEK_KEY"):
        os.environ["DEEPSEEK_KEY"] = deepseek_key
    if deepseek_key and not os.environ.get("DEEPSEEK_API_KEY"):
        os.environ["DEEPSEEK_API_KEY"] = deepseek_key
    if settings.openai_api_key and not os.environ.get("OPENAI_API_KEY"):
        os.environ["OPENAI_API_KEY"] = settings.openai_api_key
    if settings.anthropic_api_key and not os.environ.get("ANTHROPIC_API_KEY"):
        os.environ["ANTHROPIC_API_KEY"] = settings.anthropic_api_key
    if settings.mineru_token and not os.environ.get("MINERU_TOKEN"):
        os.environ["MINERU_TOKEN"] = settings.mineru_token


def _fallback_text_extraction(pdf_path: Path, work_dir: Path) -> tuple[Path, str]:
    fallback_path = work_dir / "ocr-output-fallback.md"
    write_text_layer_markdown(pdf_path, fallback_path)
    markdown = fallback_path.read_text(encoding="utf-8")
    summary = summarize_markdown_text(markdown)
    if not summary["usable"]:
        raise RuntimeError(
            "扫描版 PDF 需要 OCR，但当前未配置可用的 MINERU_TOKEN，且 PDF 文字层提取结果不足以继续。"
            " 请配置 MINERU_TOKEN，或换用带文字层的 PDF。"
        )
    return fallback_path, (
        "未检测到可用的 MINERU_TOKEN，已降级为直接提取 PDF 文字层。"
        f" 有效文本约 {summary['meaningful_chars']} 字符 / {summary['meaningful_lines']} 行。"
    )


def _save_skill_and_benchmark(task: Task, work_dir: Path) -> str:
    skill_dir = work_dir / "skill"
    chapters = sorted((skill_dir / "chapters").glob("*.md"))
    benchmark_path = work_dir / "benchmark.json"
    benchmark_results = json.loads(benchmark_path.read_text(encoding="utf-8")) if benchmark_path.exists() else []

    total = len(benchmark_results)
    with_correct = sum(1 for r in benchmark_results if r.get("with_skill", {}).get("correct"))
    without_correct = sum(1 for r in benchmark_results if r.get("without_skill", {}).get("correct"))
    delta_pct = ((with_correct - without_correct) / total * 100) if total else 0.0

    b = sum(
        1
        for r in benchmark_results
        if r.get("with_skill", {}).get("correct") and not r.get("without_skill", {}).get("correct")
    )
    c = sum(
        1
        for r in benchmark_results
        if not r.get("with_skill", {}).get("correct") and r.get("without_skill", {}).get("correct")
    )
    p_value = mcnemar_exact_p(b, c) if total else 1.0
    ci_lower, ci_upper = newcombe_diff_ci(with_correct, total, without_correct, total) if total else (0.0, 0.0)

    per_chapter: list[dict] = []
    chapters_grouped: dict[str, list[dict]] = {}
    for row in benchmark_results:
        chapters_grouped.setdefault(row.get("chapter", "未知章节"), []).append(row)
    for name, rows in sorted(chapters_grouped.items()):
        with_rate = (sum(1 for row in rows if row.get("with_skill", {}).get("correct")) / len(rows) * 100) if rows else 0.0
        without_rate = (sum(1 for row in rows if row.get("without_skill", {}).get("correct")) / len(rows) * 100) if rows else 0.0
        per_chapter.append({"chapter": name, "with_rate": round(with_rate, 1), "without_rate": round(without_rate, 1)})

    difficulty_map = {"easy": "简单", "medium": "中等", "hard": "困难"}
    per_difficulty: list[dict] = []
    for difficulty_key, difficulty_label in difficulty_map.items():
        rows = [row for row in benchmark_results if row.get("difficulty") == difficulty_key]
        if not rows:
            continue
        with_rate = sum(1 for row in rows if row.get("with_skill", {}).get("correct")) / len(rows) * 100
        without_rate = sum(1 for row in rows if row.get("without_skill", {}).get("correct")) / len(rows) * 100
        per_difficulty.append(
            {
                "level": difficulty_label,
                "with": round(with_rate, 1),
                "without": round(without_rate, 1),
            }
        )

    route_total = 0
    route_correct = 0
    for row in benchmark_results:
        expected = row.get("chapter")
        selected = row.get("with_skill", {}).get("selected_chapters", [])
        if not expected or not selected:
            continue
        route_total += 1
        if any(expected[:2] in selected_chapter for selected_chapter in selected):
            route_correct += 1
    routing_accuracy = round((route_correct / route_total * 100), 1) if route_total else 0.0

    report = build_report(benchmark_results) if benchmark_results else ""
    verdict_line = ""
    for line in report.splitlines():
        if line.startswith("  ") and ("推荐" in line or "交付" in line or "价值有限" in line):
            verdict_line = line.strip()
    verdict = verdict_line or ("已完成 benchmark" if benchmark_results else "未生成 benchmark")

    with Session(sync_engine) as db:
        skill = Skill(
            task_id=task.id,
            user_id=task.user_id,
            name=task.skill_slug or task.skill_name,
            book_title=task.book_title,
            domain=task.domain,
            visibility=task.visibility,
            skill_dir=str(skill_dir),
            chapter_count=len(chapters),
            benchmark_verdict=verdict,
            benchmark_delta=round(delta_pct, 1),
        )
        db.add(skill)
        db.flush()
        benchmark = BenchmarkResult(
            skill_id=skill.id,
            total_questions=total,
            with_correct=with_correct,
            without_correct=without_correct,
            delta_pct=round(delta_pct, 1),
            p_value=round(p_value, 4),
            ci_lower=round(ci_lower * 100, 1),
            ci_upper=round(ci_upper * 100, 1),
            verdict=verdict,
            per_chapter_json=per_chapter,
            per_difficulty_json=per_difficulty,
            routing_accuracy=routing_accuracy,
            raw_results_path=str(benchmark_path),
        )
        db.add(benchmark)
        db.commit()
        db.refresh(skill)
        return str(skill.id)


@celery_app.task(bind=True)
def run_pipeline_task(job_id: str, task_id: str):
    _ = job_id
    task_uuid = uuid.UUID(task_id)
    task = _load_task(task_uuid)
    work_dir = Path(task.work_dir)
    prompts_dir = PROMPTS_DIR
    _set_default_api_keys()

    _update_task(task_uuid, status="running", current_stage="probe", progress_pct=5, started_at=datetime.utcnow())

    try:
        publish_progress(task_id, "probe", "running", "正在探测 PDF...", progress=5)
        probe = probe_pdf(Path(task.pdf_path))
        (work_dir / "probe.json").write_text(json.dumps(probe, ensure_ascii=False, indent=2), encoding="utf-8")
        _update_task(task_uuid, current_stage="probe", progress_pct=12)
        publish_progress(task_id, "probe", "done", f"识别为 PDF，共 {probe.get('pages', 0)} 页", progress=12, extra=probe)

        publish_progress(task_id, "ocr", "running", "正在提取文本 / OCR...", progress=18)
        if probe["needs_ocr"]:
            if task.ocr_provider != "mineru":
                raise RuntimeError(f"Unsupported OCR provider: {task.ocr_provider}")
            mineru_token = os.environ.get("MINERU_TOKEN", "").strip()
            if mineru_token:
                parts = split_pdf_for_mineru(Path(task.pdf_path), parts_dir=work_dir / "ocr_parts")
                if len(parts) > 1:
                    md_paths = [ocr_pdf(part, work_dir / "ocr", token=mineru_token) for part in parts]
                    markdown_path = work_dir / "ocr" / "full-merged.md"
                    with markdown_path.open("w", encoding="utf-8") as merged:
                        for md_path in md_paths:
                            merged.write(md_path.read_text(encoding="utf-8"))
                else:
                    markdown_path = ocr_pdf(Path(task.pdf_path), work_dir / "ocr", token=mineru_token)
                cached_md = work_dir / "ocr-output.md"
                cached_md.write_text(markdown_path.read_text(encoding="utf-8"), encoding="utf-8")
                markdown_path = cached_md
            else:
                markdown_path, fallback_message = _fallback_text_extraction(Path(task.pdf_path), work_dir)
                publish_progress(
                    task_id,
                    "ocr",
                    "running",
                    fallback_message,
                    progress=24,
                    extra={"degraded": True, "mode": "text-layer-fallback"},
                )
        else:
            markdown_path = work_dir / "ocr-output.md"
            write_text_layer_markdown(Path(task.pdf_path), markdown_path)

        markdown = markdown_path.read_text(encoding="utf-8")
        _update_task(task_uuid, current_stage="ocr", progress_pct=32)
        publish_progress(task_id, "ocr", "done", f"文本已生成，共 {len(markdown)} 字符", progress=32)

        publish_progress(task_id, "split", "running", "正在切分章节...", progress=40)
        client = LLMClient.from_env(task.llm_provider)
        chapters = split_chapters(markdown, llm_client=client)
        chapters_json = [
            {
                "idx": chapter.idx,
                "title": chapter.title,
                "content": chapter.content,
                "source_strategy": chapter.source_strategy,
                "num": chapter.num,
            }
            for chapter in chapters
        ]
        (work_dir / "chapters.json").write_text(json.dumps(chapters_json, ensure_ascii=False, indent=2), encoding="utf-8")
        if len(chapters_json) < 3:
            raise RuntimeError("章节切分结果少于 3 章，无法继续")
        _update_task(task_uuid, current_stage="split", progress_pct=48)
        publish_progress(task_id, "split", "done", f"识别 {len(chapters_json)} 章", progress=48)

        publish_progress(task_id, "extract", "running", "正在抽取结构化知识...", progress=56)
        extract_all(
            chapters_json,
            work_dir / "extracted",
            client,
            prompts_dir,
            allow_partial=settings.allow_partial_skill,
        )
        _update_task(task_uuid, current_stage="extract", progress_pct=70)
        publish_progress(task_id, "extract", "done", "结构化抽取完成", progress=70)

        publish_progress(task_id, "assemble", "running", "正在组装 Skill...", progress=78)
        assemble(
            work_dir / "extracted",
            work_dir / "skill",
            task.skill_slug or task.skill_name,
            task.book_title,
            domain=task.domain or "",
            allow_partial=settings.allow_partial_skill,
        )
        _update_task(task_uuid, current_stage="assemble", progress_pct=84)
        publish_progress(task_id, "assemble", "done", "Skill 组装完成", progress=84)

        publish_progress(task_id, "bench", "running", "正在执行 benchmark...", progress=90)
        allocation_total = 12 if len(chapters_json) <= 6 else 18
        allocation = _allocate(chapters_json, total=allocation_total)
        questions = gen_questions(chapters_json, allocation, client, prompts_dir, domain=task.domain or "通用")
        if not questions:
            raise RuntimeError("Benchmark 出题失败，未生成任何题目")
        questions = questions[:allocation_total]
        (work_dir / "benchmark-questions.json").write_text(json.dumps(questions, ensure_ascii=False, indent=2), encoding="utf-8")
        run_benchmark(work_dir / "skill", questions, client, prompts_dir, output_path=work_dir / "benchmark.json")
        _update_task(task_uuid, current_stage="bench", progress_pct=98)
        publish_progress(task_id, "bench", "done", "Benchmark 完成", progress=98)

        skill_id = _save_skill_and_benchmark(task, work_dir)
        _update_task(
            task_uuid,
            status="completed",
            current_stage="done",
            progress_pct=100,
            completed_at=datetime.utcnow(),
        )
        publish_progress(task_id, "done", "completed", "编译完成", progress=100, extra={"skill_id": skill_id})
        return {"status": "completed", "task_id": task_id, "skill_id": skill_id}
    except Exception as exc:
        error_message = f"{type(exc).__name__}: {exc}"
        _update_task(
            task_uuid,
            status="failed",
            current_stage="failed",
            error_message=error_message,
            completed_at=datetime.utcnow(),
        )
        publish_progress(
            task_id,
            "failed",
            "failed",
            error_message,
            progress=100,
            extra={"traceback": traceback.format_exc(limit=5)},
        )
        raise
