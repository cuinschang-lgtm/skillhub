from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://skillhub:skillhub_dev@localhost:5432/skillhub"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "dev-secret-change-in-production"
    jwt_expire_minutes: int = 10080
    storage_dir: str = "./storage"
    deepseek_key: str = ""
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    mineru_token: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
