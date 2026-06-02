"""
UserSummary model — a living document about each user.

Auto-generated and updated by the User Summary Engine every N messages.
This is injected as Layer 1 of the RAC context, giving the AI instant
recall of who the user is without scanning the full chat history.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserSummary(Base):
    """
    Living profile summary of a user, regenerated periodically.

    Contains both a natural-language summary (~300 tokens) and
    structured data (key facts, emotional patterns, topics, etc.).

    Example summary_text:
        "Ravi is a 27-year-old software developer from Bangalore
        who values deep conversations. He has a close relationship
        with his younger sister Priya. His love language is Words
        of Affirmation. He tends toward anxious attachment..."
    """

    __tablename__ = "user_summaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )

    # ── Natural language summary (always injected to AI) ─────
    summary_text: Mapped[str] = mapped_column(Text, nullable=False, default="")

    # ── Structured data ──────────────────────────────────────
    key_facts: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )  # job, family members, hobbies, pets, etc.

    emotional_patterns: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )  # recurring emotional themes

    conversation_topics: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )  # topics discussed with frequency counts

    important_dates: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )  # birthdays, anniversaries, events mentioned

    relationship_dynamics: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )  # how they relate to others (parents, friends, partners)

    goals_and_dreams: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )  # what they want in life, career, love

    # ── Versioning ───────────────────────────────────────────
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # ── Timestamps ───────────────────────────────────────────
    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # ── Relationship ─────────────────────────────────────────
    user: Mapped[User] = relationship("User", back_populates="user_summary")

    def __repr__(self) -> str:
        return f"<UserSummary(user_id={self.user_id}, v{self.version})>"


from app.models.user import User  # noqa: E402, F811
