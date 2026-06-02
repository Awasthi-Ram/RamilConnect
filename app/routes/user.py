"""
User routes — profile CRUD and onboarding.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.models.personality import PersonalityProfile
from app.schemas.user import (
    UserProfileResponse,
    UpdateProfileRequest,
    OnboardingRequest,
    PersonalityProfileResponse,
)

router = APIRouter(prefix="/user", tags=["User"])


@router.get("/profile", response_model=UserProfileResponse)
async def get_profile(user: User = Depends(get_current_user)):
    """Get the current user's profile."""
    return UserProfileResponse.model_validate(user)


@router.put("/profile", response_model=UserProfileResponse)
async def update_profile(
    req: UpdateProfileRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update the current user's profile."""
    update_data = req.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(user, key, value)

    await db.commit()
    await db.refresh(user)
    return UserProfileResponse.model_validate(user)


@router.post("/onboarding", response_model=UserProfileResponse)
async def complete_onboarding(
    req: OnboardingRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Complete the onboarding wizard."""
    user.name = req.name
    user.bio = req.bio
    user.goal = req.goal
    user.looking_for = req.looking_for
    user.city = req.city
    user.profession = req.profession
    user.companion_persona = req.companion_persona
    user.companion_name = req.companion_name
    user.onboarding_complete = True

    # Store initial personality answers
    if req.personality_answers:
        result = await db.execute(
            select(PersonalityProfile).where(PersonalityProfile.user_id == user.id)
        )
        profile = result.scalar_one_or_none()
        if profile:
            profile.user_declared_traits = req.personality_answers

    await db.commit()
    await db.refresh(user)
    return UserProfileResponse.model_validate(user)


@router.get("/personality", response_model=PersonalityProfileResponse)
async def get_personality(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the user's personality profile."""
    result = await db.execute(
        select(PersonalityProfile).where(PersonalityProfile.user_id == user.id)
    )
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Personality profile not found",
        )

    return PersonalityProfileResponse.model_validate(profile)
