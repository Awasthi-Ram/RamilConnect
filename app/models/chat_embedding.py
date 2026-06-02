"""
ChatEmbedding model — stores vector embeddings of companion messages for RAC.

Uses pgvector for efficient cosine similarity search, enabling the AI to
recall relevant past conversations regardless of how far back they occurred.
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
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

try:
    from pgvector.sqlalchemy import Vector
except ImportError:
    # Fallback if pgvector not installed yet — allows model import
    from sqlalchemy import LargeBinary as Vector  # type: ignore


class ChatEmbedding(Base):
    """
    Vector embedding of a companion message for RAC semantic retrieval.

    Each row stores:
    - The original message text
    - Its 1536-dimensional embedding vector (text-embedding-3-small)
    - Extracted topic tags for clustering
    - Emotional valence (-1.0 negative → +1.0 positive)

    The RAC engine queries this table via cosine similarity to find
    past messages relevant to the current conversation context.
    """

    __tablename__ = "chat_embeddings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    message_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("companion_messages.id", ondelete="CASCADE"), nullable=False, unique=True
    )

    # Original content
    content_text: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # 'user' | 'assistant'

    # Vector embedding (1536 dimensions for text-embedding-3-small)
    embedding = mapped_column(Vector(1536), nullable=False)

    # Metadata for filtering/clustering
    topic_tags: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, server_default="{}")
    emotional_valence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<ChatEmbedding(id={self.id}, user_id={self.user_id}, msg_id={self.message_id})>"
