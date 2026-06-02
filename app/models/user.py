"""
User model — ported from Soul-Sync-AI Drizzle schema with enhancements.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    """Core user account table."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    dob: Mapped[str] = mapped_column(String(20), nullable=False)  # ISO date string
    gender: Mapped[str] = mapped_column(String(20), nullable=False)

    # Optional profile fields
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    profession: Mapped[str | None] = mapped_column(String(100), nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    goal: Mapped[str | None] = mapped_column(String(50), nullable=True)
    looking_for: Mapped[str | None] = mapped_column(String(50), nullable=True)
    photos: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, server_default="{}")

    # App state
    onboarding_complete: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    companion_persona: Mapped[str] = mapped_column(String(30), nullable=False, default="girlfriend")
    companion_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    personality_profile: Mapped[PersonalityProfile | None] = relationship(
        "PersonalityProfile", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    companion_sessions: Mapped[list[CompanionSession]] = relationship(
        "CompanionSession", back_populates="user", cascade="all, delete-orphan"
    )
    companion_messages: Mapped[list[CompanionMessage]] = relationship(
        "CompanionMessage", back_populates="user", cascade="all, delete-orphan"
    )
    user_summary: Mapped[UserSummary | None] = relationship(
        "UserSummary", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email!r}, name={self.name!r})>"


# Avoid circular import — these are referenced by string in relationship()
from app.models.personality import PersonalityProfile  # noqa: E402, F811
from app.models.companion import CompanionSession, CompanionMessage  # noqa: E402, F811
from app.models.user_summary import UserSummary  # noqa: E402, F811
