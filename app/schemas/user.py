"""User profile schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class UserProfileResponse(BaseModel):
    id: int
    email: str
    name: str
    dob: str
    gender: str
    city: str | None = None
    profession: str | None = None
    bio: str | None = None
    goal: str | None = None
    looking_for: str | None = None
    photos: list[str] = []
    onboarding_complete: bool
    companion_persona: str
    companion_name: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class UpdateProfileRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    city: Optional[str] = None
    profession: Optional[str] = None
    bio: Optional[str] = None
    goal: Optional[str] = None
    looking_for: Optional[str] = None
    photos: Optional[list[str]] = None


class OnboardingRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    bio: str | None = None
    goal: str | None = None
    looking_for: str | None = None
    city: str | None = None
    profession: str | None = None
    companion_persona: str = "girlfriend"
    companion_name: str | None = None
    personality_answers: dict | None = None  # Initial questionnaire answers


class PersonalityProfileResponse(BaseModel):
    big5_openness: float | None = None
    big5_conscientiousness: float | None = None
    big5_extraversion: float | None = None
    big5_agreeableness: float | None = None
    big5_neuroticism: float | None = None
    attachment_style: str | None = None
    love_languages: list[str] = []
    core_values: list[str] = []
    communication_style: str | None = None
    humor_type: str | None = None
    conflict_response: str | None = None
    emotional_depth: float | None = None
    confidence_score: float = 0.0

    class Config:
        from_attributes = True
