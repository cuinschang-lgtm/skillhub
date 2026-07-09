from __future__ import annotations

from pathlib import Path
from typing import Iterator

from pydantic_settings import BaseSettings
from pydantic import ConfigDict


APP_ROOT = Path(__file__).resolve().parents[1]


def _resolve_app_path(path_value: str) -> Path:
    path = Path(path_value).expanduser()
    if not path.is_absolute():
        path = APP_ROOT / path
    return path.resolve()


def _resolve_sqlite_database_url(url: str) -> str:
    for prefix in ("sqlite+aiosqlite:///", "sqlite:///"):
        if not url.startswith(prefix):
            continue
        raw_path = url[len(prefix) :]
        if raw_path in {"", ":memory:"} or raw_path.startswith("/"):
            return url
        return f"{prefix}{_resolve_app_path(raw_path)}"
    return url


def normalize_database_url(url: str, *, async_mode: bool) -> str:
    resolved_url = _resolve_sqlite_database_url(url)
    if resolved_url.startswith("sqlite+aiosqlite:///"):
        return resolved_url if async_mode else resolved_url.replace("sqlite+aiosqlite:///", "sqlite:///", 1)
    if resolved_url.startswith("sqlite:///"):
        return resolved_url.replace("sqlite:///", "sqlite+aiosqlite:///", 1) if async_mode else resolved_url

    normalized = resolved_url.replace("postgres://", "postgresql://", 1)
    if async_mode:
        if normalized.startswith("postgresql+asyncpg://"):
            return normalized
        if normalized.startswith("postgresql+psycopg2://"):
            return normalized.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
        if normalized.startswith("postgresql://"):
            return normalized.replace("postgresql://", "postgresql+asyncpg://", 1)
        return normalized

    if normalized.startswith("postgresql+asyncpg://"):
        return normalized.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)
    if normalized.startswith("postgresql://"):
        return normalized.replace("postgresql://", "postgresql+psycopg2://", 1)
    return normalized


def is_sqlite_database_url(url: str) -> bool:
    normalized = normalize_database_url(url, async_mode=True)
    return normalized.startswith(("sqlite:///", "sqlite+aiosqlite:///"))


def _iter_exception_chain(exc: BaseException) -> Iterator[BaseException]:
    seen: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        yield current
        current = current.__cause__ or current.__context__


def _is_database_connectivity_error(exc: BaseException) -> bool:
    for item in _iter_exception_chain(exc):
        if isinstance(item, (OSError, TimeoutError)):
            return True
        message = str(item).lower()
        if any(
            phrase in message
            for phrase in (
                "could not translate host name",
                "name or service not known",
                "temporary failure in name resolution",
                "connection refused",
                "connection timed out",
            )
        ):
            return True
    return False


def should_use_storage_sqlite_fallback(database_url: str, exc: BaseException) -> bool:
    return not is_sqlite_database_url(database_url) and _is_database_connectivity_error(exc)


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite+aiosqlite:///./storage/skillhub.db"
    redis_url: str = ""
    jwt_secret: str = "dev-secret-change-in-production"
    jwt_expire_minutes: int = 10080
    storage_dir: str = "./storage"
    deepseek_key: str = ""
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    mineru_token: str = ""
    default_llm_provider: str = "deepseek"
    allow_partial_skill: bool = False
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

settings = Settings()
settings.storage_dir = str(_resolve_app_path(settings.storage_dir))
settings.database_url = _resolve_sqlite_database_url(settings.database_url)


def storage_sqlite_database_url(*, async_mode: bool) -> str:
    sqlite_url = f"sqlite+aiosqlite:///{Path(settings.storage_dir) / 'skillhub.db'}"
    return normalize_database_url(sqlite_url, async_mode=async_mode)
