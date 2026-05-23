from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import BenchmarkResult, Skill, User


logger = logging.getLogger(__name__)

PREBUILT_DEMO_SKILL_ID = uuid.UUID("0d5dc07f-5efe-4eb8-b8c5-4bf82039d6d1")
PREBUILT_DEMO_USER_EMAIL = "prebuilt-demo-skill@skillhub.local"
PREBUILT_DEMO_SKILL_NAME = "accounting-demo-skill"
PREBUILT_DEMO_BOOK_TITLE = "中级财务会计演示版"
PREBUILT_DEMO_ASSET_DIR = Path(__file__).resolve().parent / "demo_assets" / "prebuilt-accounting-skill"
PREBUILT_DEMO_RAW_RESULTS = PREBUILT_DEMO_ASSET_DIR / "benchmark-raw-results.json"


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


def _get_session_local():
    from app.db import SessionLocal

    return SessionLocal


async def cleanup_stale_skills() -> int:
    SessionLocal = _get_session_local()
    async with SessionLocal() as session:
        result = await session.execute(select(Skill))
        skills = list(result.scalars().all())
        stale_skill_ids: list[UUID] = [skill.id for skill in skills if not _skill_dir_exists(skill)]
        if not stale_skill_ids:
            return 0

        await _delete_stale_skills(session, stale_skill_ids)
        logger.warning("Cleaned up %s stale skills with missing directories", len(stale_skill_ids))
        return len(stale_skill_ids)


async def ensure_prebuilt_demo_skill() -> str | None:
    if not PREBUILT_DEMO_ASSET_DIR.exists():
        logger.warning("Prebuilt demo skill asset directory is missing: %s", PREBUILT_DEMO_ASSET_DIR)
        return None

    SessionLocal = _get_session_local()
    async with SessionLocal() as session:
        user = await _get_or_create_demo_user(session)
        skill = await session.get(Skill, PREBUILT_DEMO_SKILL_ID)
        chapter_count = len(list((PREBUILT_DEMO_ASSET_DIR / "chapters").glob("*.md")))
        raw_results = []
        if PREBUILT_DEMO_RAW_RESULTS.exists():
            raw_results = json.loads(PREBUILT_DEMO_RAW_RESULTS.read_text(encoding="utf-8"))

        if not skill:
            skill = Skill(
                id=PREBUILT_DEMO_SKILL_ID,
                user_id=user.id,
                name=PREBUILT_DEMO_SKILL_NAME,
                book_title=PREBUILT_DEMO_BOOK_TITLE,
                domain="会计",
                visibility="public",
                skill_dir=str(PREBUILT_DEMO_ASSET_DIR),
                chapter_count=chapter_count,
                benchmark_verdict="演示预制 Skill：可直接进入结果页和问答页",
                benchmark_delta=50.0,
                benchmark_p_value=0.125,
                created_at=datetime.utcnow(),
            )
            session.add(skill)
            await session.flush()
        else:
            skill.user_id = user.id
            skill.name = PREBUILT_DEMO_SKILL_NAME
            skill.book_title = PREBUILT_DEMO_BOOK_TITLE
            skill.domain = "会计"
            skill.visibility = "public"
            skill.skill_dir = str(PREBUILT_DEMO_ASSET_DIR)
            skill.chapter_count = chapter_count
            skill.benchmark_verdict = "演示预制 Skill：可直接进入结果页和问答页"
            skill.benchmark_delta = 50.0
            skill.benchmark_p_value = 0.125

        result = await session.execute(select(BenchmarkResult).where(BenchmarkResult.skill_id == PREBUILT_DEMO_SKILL_ID))
        benchmarks = list(result.scalars().all())
        benchmark = benchmarks[0] if benchmarks else None
        for extra in benchmarks[1:]:
            await session.delete(extra)

        if not benchmark:
            benchmark = BenchmarkResult(skill_id=PREBUILT_DEMO_SKILL_ID)
            session.add(benchmark)

        benchmark.total_questions = 4
        benchmark.with_correct = 4
        benchmark.without_correct = 2
        benchmark.delta_pct = 50.0
        benchmark.p_value = 0.125
        benchmark.ci_lower = 5.0
        benchmark.ci_upper = 72.5
        benchmark.verdict = "演示预制 Skill：推荐用于结果页和问答页现场演示"
        benchmark.per_chapter_json = [
            {"chapter": "01-财务会计基础", "with_rate": 100.0, "without_rate": 0.0},
            {"chapter": "03-存货与收入确认", "with_rate": 100.0, "without_rate": 100.0},
            {"chapter": "04-长期资产", "with_rate": 100.0, "without_rate": 0.0},
            {"chapter": "06-财务报表与分析", "with_rate": 100.0, "without_rate": 100.0},
        ]
        benchmark.per_difficulty_json = [
            {"level": "简单", "with": 100.0, "without": 100.0},
            {"level": "中等", "with": 100.0, "without": 50.0},
            {"level": "困难", "with": 100.0, "without": 0.0},
        ]
        benchmark.routing_accuracy = 100.0
        benchmark.raw_results_path = str(PREBUILT_DEMO_RAW_RESULTS)

        await session.commit()
        logger.info("Prebuilt demo skill is ready: %s", PREBUILT_DEMO_SKILL_ID)
        return str(PREBUILT_DEMO_SKILL_ID)


async def _get_or_create_demo_user(session: AsyncSession) -> User:
    result = await session.execute(select(User).where(User.email == PREBUILT_DEMO_USER_EMAIL))
    user = result.scalar_one_or_none()
    if user:
        user.role = "teacher"
        user.display_name = "SkillHub Demo"
        return user

    user = User(email=PREBUILT_DEMO_USER_EMAIL, role="teacher", display_name="SkillHub Demo")
    session.add(user)
    await session.flush()
    return user


async def _delete_stale_skills(session: AsyncSession, stale_skill_ids: list[UUID]) -> None:
    await session.execute(delete(BenchmarkResult).where(BenchmarkResult.skill_id.in_(stale_skill_ids)))
    await session.execute(delete(Skill).where(Skill.id.in_(stale_skill_ids)))
    await session.commit()
