"""
Companion models — sessions and messages for AI companion chat.
Sessions track conversation boundaries; messages store the actual dialogue.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Boolean,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class CompanionSession(Base):
    """
    Tracks conversation sessions with the AI companion.

    A new session starts when the user opens a new chat or after
    a configurable idle timeout (e.g., 4 hours of inactivity).
    """

    __tablename__ = "companion_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    persona: Mapped[str] = mapped_column(String(30), nullable=False, default="girlfriend")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    message_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Timestamps
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="companion_sessions")
    messages: Mapped[list[CompanionMessage]] = relationship(
        "CompanionMessage", back_populates="session", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<CompanionSession(id={self.id}, user_id={self.user_id}, msgs={self.message_count})>"


class CompanionMessage(Base):
    """
    Individual messages in a companion conversation.

    Each message is tagged with emotion and optionally embedded
    for RAC (Retrieval-Augmented Context) search.
    """

    __tablename__ = "companion_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    session_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("companion_sessions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # 'user' | 'assistant'
    content: Mapped[str] = mapped_column(Text, nullable=False)
    emotion_tags: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, server_default="{}")

    # Whether this message has been embedded for RAC
    is_embedded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="companion_messages")
    session: Mapped[CompanionSession | None] = relationship(
        "CompanionSession", back_populates="messages"
    )

    def __repr__(self) -> str:
        return f"<CompanionMessage(id={self.id}, role={self.role!r}, len={len(self.content)})>"


from app.models.user import User  # noqa: E402, F811
