"""
config.py — Centralized settings for SafeDistrict AI.

Single source of truth for API keys, model names, and service URLs.
Every other module should call get_settings() from here instead of calling
os.getenv() directly.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, loaded from environment variables / .env."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    groq_api_key: str = Field(
        description="Required — RAGPipeline uses Groq (llama-3.3-70b-versatile) for "
        "answer generation regardless of which LLM the agent picks. Add it to your "
        ".env file: GROQ_API_KEY=gsk_..."
    )
    anthropic_api_key: str | None = None
    allowed_origins: str = "http://localhost:8501"
    backend_url: str = "http://localhost:8000"
    groq_model: str = "llama-3.3-70b-versatile"
    anthropic_model: str = "claude-sonnet-4-6"

    def __init__(self, **kwargs) -> None:
        """Wrap pydantic's ValidationError with the pre-existing, friendlier message.

        Applies to any Settings(...) construction (not just the module-level
        singleton below), so e.g. tests constructing a fresh Settings() get the
        same helpful error instead of a bare pydantic ValidationError.
        """
        try:
            super().__init__(**kwargs)
        except ValidationError as exc:
            raise OSError(
                "GROQ_API_KEY not found. Add it to your .env file:\n"
                "  GROQ_API_KEY=gsk_..."
            ) from exc


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide Settings singleton, constructed on first call."""
    return Settings()
