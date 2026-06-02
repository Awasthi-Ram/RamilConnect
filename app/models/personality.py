"""
PersonalityProfile model — Big Five, attachment, love languages, and more.
Ported from Soul-Sync-AI with enhanced fields for the psychology engine.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PersonalityProfile(Base):
    """
    Stores the AI-inferred personality profile for a user.

    Updated by the Psychology Engine every N messages via
    Bayesian weighted merge of new observations with existing profile.
    """

    __tablename__ = "personality_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )

    # ── Big Five Personality Traits (0.0 → 1.0 scale) ───────
    big5_openness: Mapped[float | None] = mapped_column(Float, nullable=True)
    big5_conscientiousness: Mapped[float | None] = mapped_column(Float, nullable=True)
    big5_extraversion: Mapped[float | None] = mapped_column(Float, nullable=True)
    big5_agreeableness: Mapped[float | None] = mapped_column(Float, nullable=True)
    big5_neuroticism: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ── Relational Psychology ────────────────────────────────
    attachment_style: Mapped[str | None] = mapped_column(
        String(30), nullable=True
    )  # secure | anxious | avoidant | disorganized
    love_languages: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, server_default="{}")
    core_values: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, server_default="{}")
    communication_style: Mapped[str | None] = mapped_column(
        String(30), nullable=True
    )  # direct | indirect | emotional | logical | mixed
    humor_type: Mapped[str | None] = mapped_column(
        String(30), nullable=True
    )  # dry | absurd | playful | self-deprecating
    conflict_response: Mapped[str | None] = mapped_column(
        String(30), nullable=True
    )  # confronts | avoids | deflects | collaborative
    emotional_depth: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ── Emotional Regulation (NEW) ───────────────────────────
    emotional_regulation: Mapped[str | None] = mapped_column(
        String(30), nullable=True
    )  # suppressive | expressive | reframing | avoidant
    stress_response: Mapped[str | None] = mapped_column(
        String(30), nullable=True
    )  # fight | flight | freeze | fawn

    # ── Trait Storage ────────────────────────────────────────
    user_declared_traits: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    ai_inferred_traits: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")

    # ── Confidence ───────────────────────────────────────────
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    extraction_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # ── Timestamps ───────────────────────────────────────────
    last_updated: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # ── Relationship ─────────────────────────────────────────
    user: Mapped[User] = relationship("User", back_populates="personality_profile")

    def __repr__(self) -> str:
        return f"<PersonalityProfile(user_id={self.user_id}, confidence={self.confidence_score:.2f})>"


from app.models.user import User  # noqa: E402, F811
