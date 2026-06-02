"""
Admin routes — dashboard, user management, config management.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func as sqlfunc, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_admin
from app.models.user import User
from app.models.companion import CompanionMessage, CompanionSession
from app.models.personality import PersonalityProfile
from app.models.user_summary import UserSummary
from app.models.admin import AdminConfig
from app.models.match import Match

router = APIRouter(prefix="/admin", tags=["Admin"])


# ── Dashboard Stats ──────────────────────────────────────────

@router.get("/stats")
async def get_dashboard_stats(
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get aggregate dashboard statistics."""
    # Total users
    user_count = await db.execute(select(sqlfunc.count()).select_from(User))
    total_users = user_count.scalar() or 0

    # Total messages
    msg_count = await db.execute(select(sqlfunc.count()).select_from(CompanionMessage))
    total_messages = msg_count.scalar() or 0

    # Active sessions
    session_count = await db.execute(
        select(sqlfunc.count())
        .select_from(CompanionSession)
        .where(CompanionSession.is_active == True)
    )
    active_sessions = session_count.scalar() or 0

    # Profiles with personality data
    profile_count = await db.execute(
        select(sqlfunc.count())
        .select_from(PersonalityProfile)
        .where(PersonalityProfile.confidence_score > 0.1)
    )
    personality_profiles = profile_count.scalar() or 0

    # Total matches
    match_count = await db.execute(select(sqlfunc.count()).select_from(Match))
    total_matches = match_count.scalar() or 0

    return {
        "total_users": total_users,
        "total_messages": total_messages,
        "active_sessions": active_sessions,
        "personality_profiles": personality_profiles,
        "total_matches": total_matches,
    }


# ── User Management ─────────────────────────────────────────

@router.get("/users")
async def list_users(
    skip: int = 0,
    limit: int = 50,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all users with basic info."""
    result = await db.execute(
        select(User)
        .order_by(desc(User.created_at))
        .offset(skip)
        .limit(limit)
    )
    users = result.scalars().all()

    return [
        {
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "gender": u.gender,
            "city": u.city,
            "companion_persona": u.companion_persona,
            "onboarding_complete": u.onboarding_complete,
            "is_admin": u.is_admin,
            "created_at": u.created_at.isoformat(),
        }
        for u in users
    ]


@router.get("/users/{user_id}")
async def get_user_detail(
    user_id: int,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed user info including personality and summary."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get personality
    profile_result = await db.execute(
        select(PersonalityProfile).where(PersonalityProfile.user_id == user_id)
    )
    profile = profile_result.scalar_one_or_none()

    # Get summary
    summary_result = await db.execute(
        select(UserSummary).where(UserSummary.user_id == user_id)
    )
    summary = summary_result.scalar_one_or_none()

    # Message count
    msg_count = await db.execute(
        select(sqlfunc.count())
        .select_from(CompanionMessage)
        .where(CompanionMessage.user_id == user_id)
    )

    return {
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "dob": user.dob,
            "gender": user.gender,
            "city": user.city,
            "profession": user.profession,
            "bio": user.bio,
            "companion_persona": user.companion_persona,
            "companion_name": user.companion_name,
            "created_at": user.created_at.isoformat(),
        },
        "personality": {
            "big5_openness": profile.big5_openness if profile else None,
            "big5_conscientiousness": profile.big5_conscientiousness if profile else None,
            "big5_extraversion": profile.big5_extraversion if profile else None,
            "big5_agreeableness": profile.big5_agreeableness if profile else None,
            "big5_neuroticism": profile.big5_neuroticism if profile else None,
            "attachment_style": profile.attachment_style if profile else None,
            "love_languages": profile.love_languages if profile else [],
            "confidence_score": profile.confidence_score if profile else 0,
            "extraction_count": profile.extraction_count if profile else 0,
        } if profile else None,
        "summary": {
            "text": summary.summary_text if summary else "",
            "key_facts": summary.key_facts if summary else {},
            "version": summary.version if summary else 0,
        } if summary else None,
        "total_messages": msg_count.scalar() or 0,
    }


@router.get("/users/{user_id}/conversations")
async def get_user_conversations(
    user_id: int,
    limit: int = 100,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get a user's conversation history."""
    result = await db.execute(
        select(CompanionMessage)
        .where(CompanionMessage.user_id == user_id)
        .order_by(desc(CompanionMessage.created_at))
        .limit(limit)
    )
    messages = list(reversed(result.scalars().all()))

    return [
        {
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "emotion_tags": m.emotion_tags,
            "created_at": m.created_at.isoformat(),
        }
        for m in messages
    ]


# ── Config Management ────────────────────────────────────────

@router.get("/config")
async def get_all_config(
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get all admin configuration values."""
    result = await db.execute(select(AdminConfig).order_by(AdminConfig.key))
    configs = result.scalars().all()
    return {c.key: {"value": c.value, "description": c.description} for c in configs}


@router.put("/config/{key}")
async def set_config(
    key: str,
    value: str,
    description: str = "",
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Set a configuration value (upsert)."""
    result = await db.execute(select(AdminConfig).where(AdminConfig.key == key))
    config = result.scalar_one_or_none()

    if config:
        config.value = value
        if description:
            config.description = description
    else:
        config = AdminConfig(key=key, value=value, description=description)
        db.add(config)

    await db.commit()
    return {"key": key, "value": value, "status": "updated"}
