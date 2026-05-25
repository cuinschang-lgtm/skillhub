from collections.abc import AsyncGenerator

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import normalize_database_url, settings
from app.maintenance import ensure_storage_ready
from app.models import Base


Base.metadata.bind = None
ensure_storage_ready(settings.storage_dir)
engine = create_async_engine(
    normalize_database_url(settings.database_url, async_mode=True),
    future=True,
    echo=False,
)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session


async def init_db() -> None:
    async with engine.begin() as conn:
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
