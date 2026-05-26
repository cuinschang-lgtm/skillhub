import json
import logging
import uuid
from pathlib import Path
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.config import settings
from app.deps import get_current_user
from app.db import get_db
from app.maintenance import PREBUILT_DEMO_ASSET_DIR
from app.models import BenchmarkResult, Skill, User

router = APIRouter()
logger = logging.getLogger(__name__)


class SkillResponse(BaseModel):
    id: str
    name: str
    book_title: str
    domain: Optional[str]
    visibility: str
    chapter_count: Optional[int]
    benchmark_verdict: Optional[str]
    benchmark_delta: Optional[float]


def _to_response(skill: Skill) -> SkillResponse:
    return SkillResponse(
        id=str(skill.id),
        name=skill.name,
        book_title=skill.book_title,
        domain=skill.domain,
        visibility=skill.visibility,
        chapter_count=skill.chapter_count,
        benchmark_verdict=skill.benchmark_verdict,
        benchmark_delta=skill.benchmark_delta,
    )


def _skill_dir_exists(skill: Skill) -> bool:
    skill_dir = (skill.skill_dir or "").strip()
    return bool(skill_dir) and Path(skill_dir).exists()


def _ensure_skill_available(skill: Skill) -> None:
    if not _skill_dir_exists(skill):
        raise HTTPException(status_code=410, detail="Skill 文件已失效，请重新编译该教材")


def _allowed_raw_results_roots() -> tuple[Path, ...]:
    return (
        Path(settings.storage_dir).resolve(),
        PREBUILT_DEMO_ASSET_DIR.resolve(),
    )


def _path_within_roots(path: Path, roots: tuple[Path, ...]) -> bool:
    for root in roots:
        try:
            path.relative_to(root)
            return True
        except ValueError:
            continue
    return False


def _load_safe_raw_results(raw_results_path: Optional[str]) -> list:
    if not raw_results_path:
        return []

    try:
        resolved_path = Path(raw_results_path).resolve()
    except (OSError, RuntimeError, ValueError):
        logger.warning("Ignore invalid benchmark raw_results_path")
        return []

    if not _path_within_roots(resolved_path, _allowed_raw_results_roots()):
        logger.warning("Ignore benchmark raw_results_path outside allowlist")
        return []

    if not resolved_path.exists() or not resolved_path.is_file():
        return []

    try:
        payload = json.loads(resolved_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        logger.warning("Ignore unreadable benchmark raw results file")
        return []

    return payload if isinstance(payload, list) else []


@router.get("")
async def list_skills(
    search: str = "",
    domain: str = "",
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = select(Skill).where(
        or_(Skill.visibility == "public", Skill.user_id == user.id)
    )
    if search:
        like = f"%{search.strip()}%"
        stmt = stmt.where(or_(Skill.book_title.ilike(like), Skill.name.ilike(like), Skill.domain.ilike(like)))
    if domain:
        stmt = stmt.where(Skill.domain.ilike(f"%{domain.strip()}%"))

    stmt = stmt.order_by(desc(Skill.created_at))
    result = await db.execute(stmt)
    visible_items = [skill for skill in result.scalars().all() if _skill_dir_exists(skill)]
    total = len(visible_items)
    start = max(0, (page - 1) * page_size)
    end = start + page_size
    items = visible_items[start:end]

    return {
        "items": [_to_response(skill).model_dump() for skill in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/{skill_id}")
async def get_skill(
    skill_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    skill = await db.get(Skill, uuid.UUID(skill_id))
    if not skill or (skill.visibility != "public" and skill.user_id != user.id):
        raise HTTPException(status_code=404, detail="Skill not found")
    _ensure_skill_available(skill)

    bench_result = await db.execute(select(BenchmarkResult).where(BenchmarkResult.skill_id == skill.id))
    bench = bench_result.scalar_one_or_none()

    data = _to_response(skill).model_dump()
    if bench:
        data["benchmark"] = {
            "total_questions": bench.total_questions,
            "with_correct": bench.with_correct,
            "without_correct": bench.without_correct,
            "delta_pct": bench.delta_pct,
            "p_value": bench.p_value,
            "ci_lower": bench.ci_lower,
            "ci_upper": bench.ci_upper,
            "verdict": bench.verdict,
            "per_chapter_json": bench.per_chapter_json,
            "per_difficulty_json": bench.per_difficulty_json,
            "routing_accuracy": bench.routing_accuracy,
        }
    return data


@router.get("/{skill_id}/chapters/{filename}")
async def get_chapter(
    skill_id: str,
    filename: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    skill = await db.get(Skill, uuid.UUID(skill_id))
    if not skill or (skill.visibility != "public" and skill.user_id != user.id):
        raise HTTPException(status_code=404, detail="Skill not found")
    _ensure_skill_available(skill)

    chapter_path = (Path(skill.skill_dir) / "chapters" / filename).resolve()
    chapters_dir = (Path(skill.skill_dir) / "chapters").resolve()
    try:
        chapter_path.relative_to(chapters_dir)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid chapter path") from exc
    if not chapter_path.exists():
        raise HTTPException(status_code=404, detail="Chapter not found")
    return {"filename": filename, "content": chapter_path.read_text(encoding="utf-8")}


@router.get("/{skill_id}/benchmark")
async def get_benchmark(
    skill_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    skill = await db.get(Skill, uuid.UUID(skill_id))
    if not skill or (skill.visibility != "public" and skill.user_id != user.id):
        raise HTTPException(status_code=404, detail="Skill not found")
    _ensure_skill_available(skill)
    bench_result = await db.execute(select(BenchmarkResult).where(BenchmarkResult.skill_id == skill.id))
    bench = bench_result.scalar_one_or_none()
    if not bench:
        raise HTTPException(status_code=404, detail="Benchmark not found")

    raw_results = _load_safe_raw_results(bench.raw_results_path)

    return {
        "skill_id": str(skill.id),
        "verdict": bench.verdict,
        "delta_pct": bench.delta_pct,
        "p_value": bench.p_value,
        "ci_lower": bench.ci_lower,
        "ci_upper": bench.ci_upper,
        "routing_accuracy": bench.routing_accuracy,
        "total_questions": bench.total_questions,
        "with_correct": bench.with_correct,
        "without_correct": bench.without_correct,
        "per_chapter": bench.per_chapter_json,
        "per_difficulty": bench.per_difficulty_json,
        "raw_results": raw_results,
    }


@router.delete("/{skill_id}")
async def delete_skill(
    skill_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    skill = await db.get(Skill, uuid.UUID(skill_id))
    if not skill or skill.user_id != user.id:
        raise HTTPException(status_code=404, detail="Skill not found")
    await db.delete(skill)
    await db.commit()
    return {"message": "deleted"}
