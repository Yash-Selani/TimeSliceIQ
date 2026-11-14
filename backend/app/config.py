from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3-flash-preview"
    GEMINI_EMBED_MODEL: str = "gemini-embedding-001"
    VECTOR_BACKEND: str = "numpy"
    YT_PROXY_URL: str | None = None
    RATE_LIMIT_PER_MINUTE: int = 60

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


try:
    settings = Settings()
except Exception:
    # Graceful fallback if .env is permission-restricted or locked
    settings = Settings(_env_file=None)


def get_settings() -> Settings:
    """Return the global Settings instance."""
    return settings
