"""
AdminConfig model — key-value config store for admin settings.
Ported from Soul-Sync-AI adminConfigTable.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AdminConfig(Base):
    """
    Key-value configuration store managed via the admin dashboard.

    Used for:
    - AI model selection (e.g., key="model", value="gemini-2.0-flash")
    - API keys (e.g., key="api_key_openai", value="sk-...")
    - Prompt overrides per persona (e.g., key="prompt_girlfriend", value="...")
    """

    __tablename__ = "admin_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    value: Mapped[str] = mapped_column(Text, nullable=False, default="")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<AdminConfig(key={self.key!r})>"
