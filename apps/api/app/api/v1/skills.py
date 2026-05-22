import json
import uuid
from pathlib import Path
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.deps import get_current_user
from app.db import get_db
from app.models import BenchmarkResult, Skill, User

router = APIRouter()


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
    data["skill_dir"] = skill.skill_dir
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

    raw_results = []
    if bench.raw_results_path and Path(bench.raw_results_path).exists():
        raw_results = json.loads(Path(bench.raw_results_path).read_text(encoding="utf-8"))

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
