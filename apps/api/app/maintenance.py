from __future__ import annotations

import logging
from pathlib import Path
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import SessionLocal
from app.models import BenchmarkResult, Skill


logger = logging.getLogger(__name__)


def ensure_storage_ready(storage_dir: str) -> Path:
    storage_path = Path(storage_dir).resolve()
    storage_path.mkdir(parents=True, exist_ok=True)

    probe_path = storage_path / ".write-test"
    probe_path.write_text("ok", encoding="utf-8")
    probe_path.unlink(missing_ok=True)
    return storage_path


def _skill_dir_exists(skill: Skill) -> bool:
    skill_dir = (skill.skill_dir or "").strip()
    return bool(skill_dir) and Path(skill_dir).exists()


async def cleanup_stale_skills() -> int:
    async with SessionLocal() as session:
        result = await session.execute(select(Skill))
        skills = list(result.scalars().all())
        stale_skill_ids: list[UUID] = [skill.id for skill in skills if not _skill_dir_exists(skill)]
        if not stale_skill_ids:
            return 0

        await _delete_stale_skills(session, stale_skill_ids)
        logger.warning("Cleaned up %s stale skills with missing directories", len(stale_skill_ids))
        return len(stale_skill_ids)


async def _delete_stale_skills(session: AsyncSession, stale_skill_ids: list[UUID]) -> None:
    await session.execute(delete(BenchmarkResult).where(BenchmarkResult.skill_id.in_(stale_skill_ids)))
    await session.execute(delete(Skill).where(Skill.id.in_(stale_skill_ids)))
    await session.commit()
