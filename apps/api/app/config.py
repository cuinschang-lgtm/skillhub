from pydantic_settings import BaseSettings
from pydantic import ConfigDict


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


settings = Settings()
