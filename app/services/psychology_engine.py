"""
Deep Psychology Engine — rule-based + AI hybrid personality profiling.

Upgrades from Soul-Sync-AI's simple 70/30 static merge to a
Bayesian-weighted, multi-signal personality extraction system.

Pipeline:
    1. Linguistic Signal Detector — regex/keyword pattern matching
    2. AI Trait Extractor — LLM-based deep analysis
    3. Trait Aggregator — Bayesian weighted merge with confidence decay
    4. Confidence Scorer — how reliable is each trait measurement
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.companion import CompanionMessage
from app.models.personality import PersonalityProfile
from app.services.ai_provider import AIConfig, complete_json

logger = logging.getLogger(__name__)


# ── Linguistic Signal Patterns ───────────────────────────────

@dataclass
class SignalResult:
    """Result from linguistic signal detection."""
    big5_openness: float | None = None
    big5_conscientiousness: float | None = None
    big5_extraversion: float | None = None
    big5_agreeableness: float | None = None
    big5_neuroticism: float | None = None
    attachment_signals: list[str] = field(default_factory=list)
    emotional_regulation: str | None = None
    confidence: float = 0.0


# Pattern markers for Big Five detection
OPENNESS_MARKERS = [
    r"\bi(?:'ve| have) been thinking about\b",
    r"\bwhat if\b",
    r"\bimagine\b",
    r"\bi wonder\b",
    r"\bcreativ",
    r"\bphilosoph",
    r"\bart\b",
    r"\bnew experience",
    r"\bcurious\b",
    r"\bexplore\b",
    r"\bidea[s]?\b",
    r"\bperspective\b",
]

CONSCIENTIOUSNESS_MARKERS = [
    r"\bi(?:'ve| have) planned\b",
    r"\borganiz",
    r"\bschedul",
    r"\bdeadline",
    r"\bgoal[s]?\b",
    r"\bresponsib",
    r"\bon time\b",
    r"\bto.?do list\b",
    r"\bprioritiz",
    r"\befficient",
]

EXTRAVERSION_MARKERS = [
    r"\bmy friends and i\b",
    r"\bparty\b",
    r"\bsocial\b",
    r"\bhang(?:ing)? out\b",
    r"\bgroup\b",
    r"\beveryone\b",
    r"\bexcit(?:ed|ing)\b",
    r"\benerg(?:y|etic)\b",
    r"\bpeople\b",
    r"!{2,}",  # multiple exclamation marks
]

AGREEABLENESS_MARKERS = [
    r"\bi understand\b",
    r"\bi agree\b",
    r"\byou'?re right\b",
    r"\bcompromise\b",
    r"\bhelp(?:ed|ing)?\b",
    r"\bkind(?:ness)?\b",
    r"\bempathy\b",
    r"\bforgive\b",
    r"\bcooperat",
    r"\bharmony\b",
]

NEUROTICISM_MARKERS = [
    r"\bi'?m worried\b",
    r"\banxious\b",
    r"\bstress(?:ed|ful)?\b",
    r"\boverwhelm",
    r"\bcan'?t stop thinking\b",
    r"\bwhat if something\b",
    r"\bi'?m scared\b",
    r"\bpanic\b",
    r"\binsomnia\b",
    r"\bself.?doubt\b",
]

ANXIOUS_ATTACHMENT_MARKERS = [
    r"\bare you still there\b",
    r"\bdo you still (?:like|love|care)\b",
    r"\bpleae don'?t leave\b",
    r"\bi need reassurance\b",
    r"\bwhy (?:didn'?t|aren'?t) you\b",
    r"\bi'?m (?:always )?afraid of being\b",
    r"\bplease respond\b",
]

AVOIDANT_ATTACHMENT_MARKERS = [
    r"\bi(?:'m| am) fine\b",
    r"\bi don'?t (?:need|want to talk about)\b",
    r"\blet'?s change the subject\b",
    r"\bi prefer being alone\b",
    r"\bindependen",
    r"\bdon'?t get too close\b",
]


def detect_linguistic_signals(text: str) -> SignalResult:
    """
    Rule-based linguistic signal detection.

    Scans user messages for keyword/pattern markers that indicate
    personality traits. Returns raw signal strengths (0-1).
    """
    text_lower = text.lower()
    result = SignalResult()

    # Count pattern matches and normalize
    def score_patterns(patterns: list[str]) -> float:
        matches = sum(1 for p in patterns if re.search(p, text_lower))
        return min(1.0, matches / max(len(patterns) * 0.3, 1))

    result.big5_openness = score_patterns(OPENNESS_MARKERS) or None
    result.big5_conscientiousness = score_patterns(CONSCIENTIOUSNESS_MARKERS) or None
    result.big5_extraversion = score_patterns(EXTRAVERSION_MARKERS) or None
    result.big5_agreeableness = score_patterns(AGREEABLENESS_MARKERS) or None
    result.big5_neuroticism = score_patterns(NEUROTICISM_MARKERS) or None

    # Attachment signals
    if score_patterns(ANXIOUS_ATTACHMENT_MARKERS) > 0.2:
        result.attachment_signals.append("anxious")
    if score_patterns(AVOIDANT_ATTACHMENT_MARKERS) > 0.2:
        result.attachment_signals.append("avoidant")

    # Confidence based on text length and signal density
    word_count = len(text.split())
    signal_count = sum(1 for v in [
        result.big5_openness, result.big5_conscientiousness,
        result.big5_extraversion, result.big5_agreeableness,
        result.big5_neuroticism,
    ] if v is not None and v > 0)

    result.confidence = min(1.0, (signal_count / 5) * (min(word_count, 500) / 200))

    return result


# ── AI Trait Extraction ──────────────────────────────────────

EXTRACTION_SYSTEM_PROMPT = """You are a psychology AI specialist trained in:
- Big Five personality model (OCEAN)
- Attachment theory (Bowlby, Ainsworth)
- Love languages (Chapman)
- Communication styles
- Emotional regulation strategies
- Conflict response patterns

Analyze the conversation below and extract personality signals.
Be CONSERVATIVE — only report signals you're confident about.
Return ONLY valid JSON, no markdown or explanation.

Return this exact JSON structure:
{
    "big5": {
        "openness": <0.0-1.0 or null>,
        "conscientiousness": <0.0-1.0 or null>,
        "extraversion": <0.0-1.0 or null>,
        "agreeableness": <0.0-1.0 or null>,
        "neuroticism": <0.0-1.0 or null>
    },
    "attachment_style": "secure|anxious|avoidant|disorganized|unclear",
    "love_languages": ["words_of_affirmation", "quality_time", "acts_of_service", "physical_touch", "gifts"],
    "communication_style": "direct|indirect|emotional|logical|mixed",
    "conflict_response": "confronts|avoids|deflects|collaborative",
    "emotional_regulation": "suppressive|expressive|reframing|avoidant",
    "stress_response": "fight|flight|freeze|fawn",
    "core_values": [],
    "emotional_depth": <0.0-1.0 or null>,
    "humor_type": "dry|absurd|playful|self_deprecating|none_detected",
    "confidence_score": <0.0-1.0>
}"""


@dataclass
class AIExtractedTraits:
    """Parsed result from AI trait extraction."""
    big5_openness: float | None = None
    big5_conscientiousness: float | None = None
    big5_extraversion: float | None = None
    big5_agreeableness: float | None = None
    big5_neuroticism: float | None = None
    attachment_style: str | None = None
    love_languages: list[str] = field(default_factory=list)
    communication_style: str | None = None
    conflict_response: str | None = None
    emotional_regulation: str | None = None
    stress_response: str | None = None
    core_values: list[str] = field(default_factory=list)
    emotional_depth: float | None = None
    humor_type: str | None = None
    confidence_score: float = 0.0


async def extract_traits_with_ai(
    conversation_text: str,
    config: AIConfig,
) -> AIExtractedTraits:
    """Use LLM to extract personality traits from conversation."""
    try:
        response_text = await complete_json(
            system_prompt=EXTRACTION_SYSTEM_PROMPT,
            user_prompt=f"Analyze this conversation:\n\n{conversation_text}",
            config=config,
            max_tokens=500,
        )

        # Clean up potential markdown formatting
        response_text = response_text.strip()
        if response_text.startswith("```"):
            response_text = response_text.split("\n", 1)[1]
            response_text = response_text.rsplit("```", 1)[0]

        data = json.loads(response_text)

        return AIExtractedTraits(
            big5_openness=data.get("big5", {}).get("openness"),
            big5_conscientiousness=data.get("big5", {}).get("conscientiousness"),
            big5_extraversion=data.get("big5", {}).get("extraversion"),
            big5_agreeableness=data.get("big5", {}).get("agreeableness"),
            big5_neuroticism=data.get("big5", {}).get("neuroticism"),
            attachment_style=data.get("attachment_style"),
            love_languages=data.get("love_languages", []),
            communication_style=data.get("communication_style"),
            conflict_response=data.get("conflict_response"),
            emotional_regulation=data.get("emotional_regulation"),
            stress_response=data.get("stress_response"),
            core_values=data.get("core_values", []),
            emotional_depth=data.get("emotional_depth"),
            humor_type=data.get("humor_type"),
            confidence_score=data.get("confidence_score", 0.0),
        )

    except Exception as e:
        logger.error(f"AI trait extraction failed: {e}")
        return AIExtractedTraits()


# ── Bayesian Weighted Merge ──────────────────────────────────

def bayesian_merge(
    existing: float | None,
    new_value: float | None,
    existing_confidence: float,
    new_confidence: float,
    decay_factor: float = 0.95,
) -> float | None:
    """
    Bayesian weighted merge of personality trait values.

    Unlike the old 70/30 static merge, this weights by confidence:
    - Higher confidence new signals have more influence
    - Existing values decay slightly (recency bias)
    - Contradictory signals are handled gracefully
    """
    if new_value is None:
        return existing
    if existing is None:
        return new_value

    # Apply decay to existing confidence
    adj_existing_conf = existing_confidence * decay_factor
    total_confidence = adj_existing_conf + new_confidence

    if total_confidence == 0:
        return (existing + new_value) / 2

    # Weighted average based on confidence
    merged = (existing * adj_existing_conf + new_value * new_confidence) / total_confidence
    return max(0.0, min(1.0, merged))


# ── Psychology Engine ────────────────────────────────────────

class PsychologyEngine:
    """
    Deep psychology profiling engine.

    Combines rule-based linguistic analysis with AI-powered trait extraction,
    then merges results using Bayesian weighted averaging.
    """

    # How many messages to analyze per extraction
    ANALYSIS_WINDOW = 20

    # Trigger extraction every N user messages
    EXTRACTION_INTERVAL = 5

    def __init__(self, db: AsyncSession):
        self.db = db

    async def should_extract(self, user_id: int) -> bool:
        """Check if we should trigger a new extraction."""
        result = await self.db.execute(
            select(CompanionMessage)
            .where(
                CompanionMessage.user_id == user_id,
                CompanionMessage.role == "user",
            )
        )
        total_user_messages = len(result.scalars().all())
        return total_user_messages > 0 and total_user_messages % self.EXTRACTION_INTERVAL == 0

    async def extract_and_update(
        self,
        user_id: int,
        config: AIConfig,
    ) -> None:
        """
        Full extraction pipeline:
        1. Gather recent messages
        2. Run linguistic signal detection (rule-based)
        3. Run AI trait extraction (LLM-based)
        4. Merge results with Bayesian weighting
        5. Update personality profile in DB
        """
        try:
            # Get recent messages
            result = await self.db.execute(
                select(CompanionMessage)
                .where(CompanionMessage.user_id == user_id)
                .order_by(CompanionMessage.created_at.desc())
                .limit(self.ANALYSIS_WINDOW)
            )
            messages = list(reversed(result.scalars().all()))

            if not messages:
                return

            # Prepare conversation text
            conversation_text = "\n".join(
                f"{m.role}: {m.content}" for m in messages
            )

            # Only analyze user messages for linguistic signals
            user_text = " ".join(
                m.content for m in messages if m.role == "user"
            )

            # Step 1: Rule-based signal detection
            linguistic_signals = detect_linguistic_signals(user_text)

            # Step 2: AI trait extraction
            ai_traits = await extract_traits_with_ai(conversation_text, config)

            # Step 3: Get existing profile
            profile_result = await self.db.execute(
                select(PersonalityProfile)
                .where(PersonalityProfile.user_id == user_id)
            )
            profile = profile_result.scalar_one_or_none()

            if not profile:
                # Create initial profile
                profile = PersonalityProfile(user_id=user_id)
                self.db.add(profile)

            # Step 4: Bayesian merge
            existing_conf = profile.confidence_score or 0.0
            new_conf = max(
                linguistic_signals.confidence,
                ai_traits.confidence_score,
            )

            # Merge Big Five — combine rule-based and AI signals
            profile.big5_openness = bayesian_merge(
                profile.big5_openness,
                self._blend(linguistic_signals.big5_openness, ai_traits.big5_openness),
                existing_conf, new_conf,
            )
            profile.big5_conscientiousness = bayesian_merge(
                profile.big5_conscientiousness,
                self._blend(linguistic_signals.big5_conscientiousness, ai_traits.big5_conscientiousness),
                existing_conf, new_conf,
            )
            profile.big5_extraversion = bayesian_merge(
                profile.big5_extraversion,
                self._blend(linguistic_signals.big5_extraversion, ai_traits.big5_extraversion),
                existing_conf, new_conf,
            )
            profile.big5_agreeableness = bayesian_merge(
                profile.big5_agreeableness,
                self._blend(linguistic_signals.big5_agreeableness, ai_traits.big5_agreeableness),
                existing_conf, new_conf,
            )
            profile.big5_neuroticism = bayesian_merge(
                profile.big5_neuroticism,
                self._blend(linguistic_signals.big5_neuroticism, ai_traits.big5_neuroticism),
                existing_conf, new_conf,
            )
            profile.emotional_depth = bayesian_merge(
                profile.emotional_depth,
                ai_traits.emotional_depth,
                existing_conf, new_conf,
            )

            # Update categorical traits (AI-driven)
            if ai_traits.attachment_style and ai_traits.attachment_style != "unclear":
                profile.attachment_style = ai_traits.attachment_style
            if ai_traits.love_languages:
                profile.love_languages = ai_traits.love_languages
            if ai_traits.communication_style:
                profile.communication_style = ai_traits.communication_style
            if ai_traits.conflict_response:
                profile.conflict_response = ai_traits.conflict_response
            if ai_traits.emotional_regulation:
                profile.emotional_regulation = ai_traits.emotional_regulation
            if ai_traits.stress_response:
                profile.stress_response = ai_traits.stress_response
            if ai_traits.core_values:
                profile.core_values = ai_traits.core_values
            if ai_traits.humor_type:
                profile.humor_type = ai_traits.humor_type

            # Update merged AI traits JSON
            existing_ai_traits = profile.ai_inferred_traits or {}
            existing_ai_traits.update({
                "big5": {
                    "openness": profile.big5_openness,
                    "conscientiousness": profile.big5_conscientiousness,
                    "extraversion": profile.big5_extraversion,
                    "agreeableness": profile.big5_agreeableness,
                    "neuroticism": profile.big5_neuroticism,
                },
                "attachment_style": profile.attachment_style,
                "love_languages": profile.love_languages,
                "last_extraction": datetime.utcnow().isoformat(),
            })
            profile.ai_inferred_traits = existing_ai_traits

            # Update confidence (grows with each extraction, max 1.0)
            profile.confidence_score = min(
                1.0,
                bayesian_merge(
                    existing_conf, new_conf, 0.7, 0.3
                ) or 0.0
            )
            profile.extraction_count = (profile.extraction_count or 0) + 1
            profile.last_updated = datetime.utcnow()

            await self.db.commit()
            logger.info(
                f"Psychology extraction #{profile.extraction_count} for user {user_id} "
                f"(confidence: {profile.confidence_score:.2%})"
            )

        except Exception as e:
            logger.error(f"Psychology extraction failed for user {user_id}: {e}")
            await self.db.rollback()

    @staticmethod
    def _blend(rule_value: float | None, ai_value: float | None) -> float | None:
        """Blend rule-based and AI signals (60% AI, 40% rules when both present)."""
        if rule_value is None and ai_value is None:
            return None
        if rule_value is None:
            return ai_value
        if ai_value is None:
            return rule_value
        return ai_value * 0.6 + rule_value * 0.4
