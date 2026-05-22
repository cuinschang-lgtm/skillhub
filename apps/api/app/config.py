from pydantic_settings import BaseSettings
from pydantic import ConfigDict


def normalize_database_url(url: str, *, async_mode: bool) -> str:
    if url.startswith("sqlite:///") or url.startswith("sqlite+aiosqlite:///"):
        return url if async_mode else url.replace("+aiosqlite", "")

    normalized = url.replace("postgres://", "postgresql://", 1)
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
