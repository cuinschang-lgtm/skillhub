from pathlib import Path

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
    if resolved_url.startswith("sqlite:///") or resolved_url.startswith("sqlite+aiosqlite:///"):
        return resolved_url if async_mode else resolved_url.replace("+aiosqlite", "")

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
