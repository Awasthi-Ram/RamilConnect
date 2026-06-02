"""Companion chat schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class SendMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=5000)


class CompanionMessageResponse(BaseModel):
    id: int
    role: str  # 'user' | 'assistant'
    content: str
    created_at: datetime
    emotion_tags: list[str] = []

    class Config:
        from_attributes = True


class ChatHistoryResponse(BaseModel):
    messages: list[CompanionMessageResponse]
    total: int


class SwitchPersonaRequest(BaseModel):
    persona: str = Field(description="girlfriend | boyfriend | friend | relationship_guru")
    name: str | None = None


class MoodResponse(BaseModel):
    mood: str  # happy | neutral | stressed | curious | sad
    confidence: float


class CompanionStatsResponse(BaseModel):
    total_messages: int
    streak_days: int
    last_chat_date: str | None = None
    personality_confidence: float
