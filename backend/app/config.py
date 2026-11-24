from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AlphaAI"
    app_env: str = "development"
    database_url: str = "sqlite:///./alphaai.db"
    redis_url: str = "redis://localhost:6379/0"
    huggingface_token: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
