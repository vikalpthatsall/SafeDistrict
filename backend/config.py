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

# Field name -> the .env hint to show when that field is the one missing.
# Module-level, not a class attribute — pydantic intercepts underscore-prefixed
# *class* attribute access on a BaseModel/BaseSettings subclass as a private-
# attribute lookup (fails during __init__, before private attrs are set up),
# confirmed by actually hitting that AttributeError, not assumed.
_MISSING_FIELD_HINTS = {
    "groq_api_key": "  GROQ_API_KEY=gsk_...",
    "backend_api_key": "  BACKEND_API_KEY=<a long random secret>",
}


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
    backend_api_key: str = Field(
        description="Required — shared secret every non-health route requires via the "
        "X-API-Key header (see backend.main.verify_api_key). Add it to your .env file: "
        "BACKEND_API_KEY=<a long random secret>"
    )

    def __init__(self, **kwargs) -> None:
        """Wrap pydantic's ValidationError with a friendlier, field-accurate message.

        Applies to any Settings(...) construction (not just the module-level
        singleton below), so e.g. tests constructing a fresh Settings() get the
        same helpful error instead of a bare pydantic ValidationError. Reports
        every missing required field, not just whichever one happened to be
        checked first — with two required fields now, a hardcoded single-field
        message would misreport which one is actually missing.
        """
        try:
            super().__init__(**kwargs)
        except ValidationError as exc:
            missing = [e["loc"][0] for e in exc.errors() if e["type"] == "missing"]
            hints = [_MISSING_FIELD_HINTS[f] for f in missing if f in _MISSING_FIELD_HINTS]
            if not hints:
                raise
            raise OSError(
                "Required setting(s) not found. Add to your .env file:\n" + "\n".join(hints)
            ) from exc


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide Settings singleton, constructed on first call."""
    return Settings()
