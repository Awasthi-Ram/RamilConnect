"""
User Summary Engine — generates and maintains a living profile document.

This summary is injected as Layer 1 of the RAC context, giving the AI
instant recall of who the user is without scanning the full history.

Updated every SUMMARY_UPDATE_INTERVAL messages.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime

from sqlalchemy import select, desc, func as sqlfunc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.companion import CompanionMessage
from app.models.user import User
from app.models.user_summary import UserSummary
from app.services.ai_provider import AIConfig, complete_json

logger = logging.getLogger(__name__)

# Update summary every N user messages
SUMMARY_UPDATE_INTERVAL = 10


SUMMARY_SYSTEM_PROMPT = """You are a psychological profile summarizer for an AI companion app.
Your job is to create and update a living profile of the user based on their conversations.

Create a comprehensive but concise profile covering:
1. SUMMARY: A natural language paragraph (max 200 words) describing who this person is
2. KEY_FACTS: Structured data about their life (job, family, hobbies, location, pets, etc.)
3. EMOTIONAL_PATTERNS: Recurring emotional themes and how they process feelings
4. CONVERSATION_TOPICS: Topics they discuss most with rough frequency
5. IMPORTANT_DATES: Any birthdays, events, anniversaries they've mentioned
6. RELATIONSHIP_DYNAMICS: How they relate to people in their life
7. GOALS_AND_DREAMS: What they want in life, career, and love

Rules:
- Be specific and factual — only include things actually mentioned
- Note contradictions or changes in stated preferences
- Prioritize recent information over older
- Include emotional nuances, not just facts
- Keep the SUMMARY warm and empathetic in tone
- Return ONLY valid JSON, no markdown

Return this JSON structure:
{
    "summary_text": "Natural language paragraph about who this person is...",
    "key_facts": {"job": "...", "family": {...}, "hobbies": [...], ...},
    "emotional_patterns": {"recurring_themes": [...], "processing_style": "..."},
    "conversation_topics": {"topic_name": frequency_count, ...},
    "important_dates": {"event_name": "date_or_description", ...},
    "relationship_dynamics": {"person_or_role": "description", ...},
    "goals_and_dreams": {"life": [...], "career": [...], "love": [...]}
}"""


class UserSummaryEngine:
    """
    Generates and maintains a living profile summary for each user.

    The summary captures who the user is across their entire conversation
    history, allowing the AI companion to recall personal details naturally.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def should_update(self, user_id: int) -> bool:
        """Check if summary needs updating based on message count."""
        result = await self.db.execute(
            select(sqlfunc.count())
            .select_from(CompanionMessage)
            .where(
                CompanionMessage.user_id == user_id,
                CompanionMessage.role == "user",
            )
        )
        total_user_messages = result.scalar() or 0

        if total_user_messages < 5:
            return False  # Too early for meaningful summary

        return total_user_messages % SUMMARY_UPDATE_INTERVAL == 0

    async def generate_or_update(
        self,
        user_id: int,
        config: AIConfig,
    ) -> None:
        """
        Generate a new summary or update existing one.

        Sends conversation history + existing summary to the AI
        for an updated profile.
        """
        try:
            # Get user info
            user_result = await self.db.execute(
                select(User).where(User.id == user_id)
            )
            user = user_result.scalar_one_or_none()
            if not user:
                return

            # Get existing summary
            summary_result = await self.db.execute(
                select(UserSummary).where(UserSummary.user_id == user_id)
            )
            existing_summary = summary_result.scalar_one_or_none()

            # Get recent conversation history (last 50 messages for context)
            msg_result = await self.db.execute(
                select(CompanionMessage)
                .where(CompanionMessage.user_id == user_id)
                .order_by(desc(CompanionMessage.created_at))
                .limit(50)
            )
            messages = list(reversed(msg_result.scalars().all()))

            if not messages:
                return

            conversation_text = "\n".join(
                f"{m.role}: {m.content}" for m in messages
            )

            # Build the prompt
            prompt_parts = [
                f"User: {user.name}, Age DOB: {user.dob}, Gender: {user.gender}",
                f"City: {user.city or 'Unknown'}, Profession: {user.profession or 'Unknown'}",
                "",
                "=== CONVERSATION HISTORY ===",
                conversation_text,
            ]

            if existing_summary:
                prompt_parts.extend([
                    "",
                    "=== EXISTING SUMMARY (update with new info) ===",
                    existing_summary.summary_text,
                    "",
                    f"Existing key facts: {json.dumps(existing_summary.key_facts)}",
                    f"Existing topics: {json.dumps(existing_summary.conversation_topics)}",
                ])

            user_prompt = "\n".join(prompt_parts)

            # Call AI for summary generation
            response_text = await complete_json(
                system_prompt=SUMMARY_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                config=config,
                max_tokens=800,
            )

            # Parse response
            response_text = response_text.strip()
            if response_text.startswith("```"):
                response_text = response_text.split("\n", 1)[1]
                response_text = response_text.rsplit("```", 1)[0]

            data = json.loads(response_text)

            # Update or create summary
            if existing_summary:
                existing_summary.summary_text = data.get("summary_text", existing_summary.summary_text)
                existing_summary.key_facts = data.get("key_facts", existing_summary.key_facts)
                existing_summary.emotional_patterns = data.get("emotional_patterns", existing_summary.emotional_patterns)
                existing_summary.conversation_topics = data.get("conversation_topics", existing_summary.conversation_topics)
                existing_summary.important_dates = data.get("important_dates", existing_summary.important_dates)
                existing_summary.relationship_dynamics = data.get("relationship_dynamics", existing_summary.relationship_dynamics)
                existing_summary.goals_and_dreams = data.get("goals_and_dreams", existing_summary.goals_and_dreams)
                existing_summary.version += 1
                existing_summary.last_updated = datetime.utcnow()
            else:
                new_summary = UserSummary(
                    user_id=user_id,
                    summary_text=data.get("summary_text", ""),
                    key_facts=data.get("key_facts", {}),
                    emotional_patterns=data.get("emotional_patterns", {}),
                    conversation_topics=data.get("conversation_topics", {}),
                    important_dates=data.get("important_dates", {}),
                    relationship_dynamics=data.get("relationship_dynamics", {}),
                    goals_and_dreams=data.get("goals_and_dreams", {}),
                    version=1,
                )
                self.db.add(new_summary)

            await self.db.commit()
            version = existing_summary.version if existing_summary else 1
            logger.info(f"User summary v{version} updated for user {user_id}")

        except Exception as e:
            logger.error(f"User summary generation failed for user {user_id}: {e}")
            await self.db.rollback()
