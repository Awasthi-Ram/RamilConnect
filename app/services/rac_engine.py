"""
RAC Engine — Retrieval-Augmented Context.

The core innovation of RamilConnect. Assembles a multi-layer context
window so the AI companion never loses context about the user, no matter
how far back a conversation occurred.

4 Layers:
    1. User Summary     — Living profile (~300 tokens, always injected)
    2. Session Memory   — Current conversation (last 15 messages)
    3. Semantic Retrieval — pgvector search for relevant past conversations
    4. Psychology Snapshot — Current personality + mood + patterns
"""

from __future__ import annotations

import logging
from typing import List

from sqlalchemy import select, desc, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.companion import CompanionMessage
from app.models.chat_embedding import ChatEmbedding
from app.models.personality import PersonalityProfile
from app.models.user_summary import UserSummary
from app.utils.embeddings import get_embedding, EMBEDDING_DIM

logger = logging.getLogger(__name__)


class RACEngine:
    """
    Retrieval-Augmented Context engine.

    Assembles a multi-layer context window for the AI companion,
    ensuring context is never lost regardless of conversation length.
    """

    # Token budgets per layer (approximate)
    SUMMARY_TOKEN_BUDGET = 300
    SESSION_TOKEN_BUDGET = 1500
    RETRIEVAL_TOKEN_BUDGET = 800
    PSYCHOLOGY_TOKEN_BUDGET = 200

    # How many recent messages to include as session memory
    SESSION_MESSAGE_LIMIT = 15

    # How many semantically similar past messages to retrieve
    RETRIEVAL_TOP_K = 5

    def __init__(self, db: AsyncSession):
        self.db = db

    async def assemble_context(
        self,
        user_id: int,
        current_message: str,
        session_id: int | None = None,
    ) -> str:
        """
        Assemble the full RAC context for a companion message.

        Returns a formatted context string to be prepended to the system prompt.
        """
        layers = []

        # ── Layer 1: User Summary ────────────────────────────
        summary = await self._get_user_summary(user_id)
        if summary:
            layers.append(f"[USER MEMORY — Who This Person Is]\n{summary}")

        # ── Layer 2: Session Memory (recent messages) ────────
        session_context = await self._get_session_memory(user_id, session_id)
        if session_context:
            layers.append(f"[RECENT CONVERSATION CONTEXT]\n{session_context}")

        # ── Layer 3: Semantic Retrieval ──────────────────────
        relevant_past = await self._semantic_retrieval(user_id, current_message)
        if relevant_past:
            layers.append(f"[RELEVANT PAST CONVERSATIONS — Use naturally, don't quote]\n{relevant_past}")

        # ── Layer 4: Psychology Snapshot ──────────────────────
        psych = await self._get_psychology_snapshot(user_id)
        if psych:
            layers.append(f"[PSYCHOLOGY PROFILE]\n{psych}")

        if not layers:
            return ""

        return "\n\n---\n\n".join(layers)

    # ── Layer 1: User Summary ────────────────────────────────

    async def _get_user_summary(self, user_id: int) -> str | None:
        """Retrieve the living user summary."""
        result = await self.db.execute(
            select(UserSummary).where(UserSummary.user_id == user_id)
        )
        summary = result.scalar_one_or_none()
        if summary and summary.summary_text:
            return summary.summary_text
        return None

    # ── Layer 2: Session Memory ──────────────────────────────

    async def _get_session_memory(
        self, user_id: int, session_id: int | None
    ) -> str | None:
        """Get recent messages from the current session."""
        query = (
            select(CompanionMessage)
            .where(CompanionMessage.user_id == user_id)
            .order_by(desc(CompanionMessage.created_at))
            .limit(self.SESSION_MESSAGE_LIMIT)
        )
        if session_id:
            query = query.where(CompanionMessage.session_id == session_id)

        result = await self.db.execute(query)
        messages = list(reversed(result.scalars().all()))

        if not messages:
            return None

        lines = []
        for msg in messages:
            role_label = "User" if msg.role == "user" else "Companion"
            lines.append(f"{role_label}: {msg.content}")

        return "\n".join(lines)

    # ── Layer 3: Semantic Retrieval ──────────────────────────

    async def _semantic_retrieval(
        self, user_id: int, current_message: str
    ) -> str | None:
        """
        Find past messages semantically relevant to the current message
        using pgvector cosine similarity search.
        """
        try:
            # Generate embedding for current message
            query_embedding = await get_embedding(current_message)

            # Check if all zeros (no API key configured)
            if all(v == 0.0 for v in query_embedding):
                return None

            # pgvector cosine distance query (lower = more similar)
            embedding_str = "[" + ",".join(str(v) for v in query_embedding) + "]"

            sql = text(f"""
                SELECT content_text, role, emotional_valence,
                       embedding <=> :query_vec AS distance
                FROM chat_embeddings
                WHERE user_id = :user_id
                ORDER BY embedding <=> :query_vec
                LIMIT :top_k
            """)

            result = await self.db.execute(
                sql,
                {
                    "query_vec": embedding_str,
                    "user_id": user_id,
                    "top_k": self.RETRIEVAL_TOP_K,
                },
            )
            rows = result.fetchall()

            if not rows:
                return None

            # Filter out very dissimilar results (distance > 0.5)
            relevant = [r for r in rows if r.distance < 0.5]
            if not relevant:
                return None

            lines = []
            for row in relevant:
                role_label = "User" if row.role == "user" else "Companion"
                lines.append(f"• {role_label} (past): {row.content_text}")

            return "\n".join(lines)

        except Exception as e:
            logger.warning(f"Semantic retrieval failed: {e}")
            return None

    # ── Layer 4: Psychology Snapshot ──────────────────────────

    async def _get_psychology_snapshot(self, user_id: int) -> str | None:
        """Get a concise psychology snapshot for context."""
        result = await self.db.execute(
            select(PersonalityProfile).where(PersonalityProfile.user_id == user_id)
        )
        profile = result.scalar_one_or_none()

        if not profile:
            return None

        parts = []

        # Big Five summary
        big5 = []
        if profile.big5_openness is not None:
            big5.append(f"Openness: {profile.big5_openness:.1%}")
        if profile.big5_conscientiousness is not None:
            big5.append(f"Conscientiousness: {profile.big5_conscientiousness:.1%}")
        if profile.big5_extraversion is not None:
            big5.append(f"Extraversion: {profile.big5_extraversion:.1%}")
        if profile.big5_agreeableness is not None:
            big5.append(f"Agreeableness: {profile.big5_agreeableness:.1%}")
        if profile.big5_neuroticism is not None:
            big5.append(f"Neuroticism: {profile.big5_neuroticism:.1%}")
        if big5:
            parts.append("Big Five: " + ", ".join(big5))

        if profile.attachment_style:
            parts.append(f"Attachment: {profile.attachment_style}")
        if profile.love_languages:
            parts.append(f"Love Languages: {', '.join(profile.love_languages)}")
        if profile.communication_style:
            parts.append(f"Communication: {profile.communication_style}")
        if profile.emotional_regulation:
            parts.append(f"Emotional Regulation: {profile.emotional_regulation}")
        if profile.conflict_response:
            parts.append(f"Conflict Response: {profile.conflict_response}")

        parts.append(f"Profile Confidence: {profile.confidence_score:.0%}")

        return "\n".join(parts)

    # ── Embedding Storage ────────────────────────────────────

    async def embed_and_store(
        self,
        user_id: int,
        message_id: int,
        content: str,
        role: str,
    ) -> None:
        """
        Embed a message and store it in chat_embeddings for future retrieval.
        Called asynchronously after each message is saved.
        """
        try:
            embedding = await get_embedding(content)

            # Skip if no real embedding (all zeros)
            if all(v == 0.0 for v in embedding):
                return

            chat_embedding = ChatEmbedding(
                user_id=user_id,
                message_id=message_id,
                content_text=content,
                role=role,
                embedding=embedding,
                topic_tags=[],
                emotional_valence=0.0,
            )
            self.db.add(chat_embedding)

            # Mark the message as embedded
            result = await self.db.execute(
                select(CompanionMessage).where(CompanionMessage.id == message_id)
            )
            msg = result.scalar_one_or_none()
            if msg:
                msg.is_embedded = True

            await self.db.commit()
            logger.info(f"Embedded message {message_id} for user {user_id}")

        except Exception as e:
            logger.error(f"Failed to embed message {message_id}: {e}")
            await self.db.rollback()
