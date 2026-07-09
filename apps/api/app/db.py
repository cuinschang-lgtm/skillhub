from collections.abc import AsyncGenerator
import logging
import os

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.config import (
    normalize_database_url,
    settings,
    should_use_storage_sqlite_fallback,
    storage_sqlite_database_url,
)
from app.maintenance import ensure_storage_ready
from app.models import Base


logger = logging.getLogger(__name__)
Base.metadata.bind = None
ensure_storage_ready(settings.storage_dir)


def _create_engine(database_url: str) -> AsyncEngine:
    return create_async_engine(
        normalize_database_url(database_url, async_mode=True),
        future=True,
        echo=False,
    )


engine = _create_engine(settings.database_url)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


def get_engine() -> AsyncEngine:
    return engine


async def use_database_url(database_url: str) -> str:
    global engine

    normalized_url = normalize_database_url(database_url, async_mode=True)
    old_engine = engine
    settings.database_url = normalized_url
    os.environ["DATABASE_URL"] = normalized_url
    engine = _create_engine(normalized_url)
    SessionLocal.configure(bind=engine)
    await old_engine.dispose()
    return normalized_url


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session


async def init_db() -> None:
    try:
        await _init_db_with_engine(engine)
    except Exception as exc:
        fallback_url = storage_sqlite_database_url(async_mode=True)
        current_url = normalize_database_url(settings.database_url, async_mode=True)
        if current_url == fallback_url or not should_use_storage_sqlite_fallback(current_url, exc):
            raise

        logger.warning(
            "Database connection failed (%s: %s); falling back to persistent SQLite at %s",
            type(exc).__name__,
            exc,
            fallback_url,
        )
        await use_database_url(fallback_url)
        await _init_db_with_engine(engine)


async def _init_db_with_engine(database_engine: AsyncEngine) -> None:
    async with database_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_ensure_legacy_schema_compatibility)


def _ensure_legacy_schema_compatibility(sync_conn) -> None:
    inspector = inspect(sync_conn)
    table_names = set(inspector.get_table_names())
    if "tasks" not in table_names:
        return

    task_columns = {column["name"] for column in inspector.get_columns("tasks")}
    if "skill_slug" not in task_columns:
        sync_conn.execute(
            text("ALTER TABLE tasks ADD COLUMN skill_slug VARCHAR(64) DEFAULT 'textbook-skill'")
        )

    sync_conn.execute(
        text(
            "UPDATE tasks "
            "SET skill_slug = COALESCE(NULLIF(skill_slug, ''), NULLIF(skill_name, ''), 'textbook-skill') "
            "WHERE skill_slug IS NULL OR skill_slug = ''"
        )
    )
