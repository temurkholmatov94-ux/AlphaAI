from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AlphaAI"
    app_env: str = "production"
    database_url: str = "sqlite:///./alphaai.db"
    redis_url: str = "redis://localhost:6379/0"
    huggingface_token: str | None = None
    alphaai_secret_key: str = ""
    alphaai_bootstrap_token: str | None = None
    access_token_minutes: int = 30

    openai_api_key: str | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    anthropic_api_key: str | None = None
    anthropic_base_url: str = "https://api.anthropic.com"
    xai_api_key: str | None = None
    xai_base_url: str = "https://api.x.ai/v1"
    alphaai_model_routes: list[str] = []
    alphaai_admin_emails: list[str] = []

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
