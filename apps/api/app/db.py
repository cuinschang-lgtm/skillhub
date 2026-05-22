from collections.abc import AsyncGenerator

from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import normalize_database_url, settings
from app.models import Base


Base.metadata.bind = None
Path(settings.storage_dir).mkdir(parents=True, exist_ok=True)
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
