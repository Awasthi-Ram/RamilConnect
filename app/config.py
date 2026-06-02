"""
RamilConnect Configuration — pydantic-settings based.

All settings are loaded from environment variables or .env file.
"""

from __future__ import annotations

import json
from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ──────────────────────────────────────────────────
    app_name: str = "RamilConnect"
    app_env: str = "development"
    debug: bool = True

    # ── Database ─────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://postgres:password@localhost:5432/ramilconnect"

    # ── JWT Auth ─────────────────────────────────────────────
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 30

    # ── AI Providers ─────────────────────────────────────────
    gemini_api_key: str = ""
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    default_ai_model: str = "gemini-2.0-flash"
    embedding_model: str = "text-embedding-3-small"

    # ── Redis ────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ── CORS ─────────────────────────────────────────────────
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:8080"]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return json.loads(v)
        return v

    # ── Admin ────────────────────────────────────────────────
    admin_email: str = "admin@ramilconnect.ai"
    admin_password: str = "change-this-password"

    # ── Derived properties ───────────────────────────────────
    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache()
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
