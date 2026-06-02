"""
Auth routes — register, login, token refresh.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.personality import PersonalityProfile
from app.models.user_summary import UserSummary
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    RefreshRequest,
    TokenResponse,
    UserBasic,
)
from app.utils.security import (
    hash_password,
    verify_password,
    create_token_pair,
    decode_token,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    req: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """Register a new user account."""
    # Check if email already exists
    existing = await db.execute(
        select(User).where(User.email == req.email)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # Create user
    user = User(
        email=req.email,
        password_hash=hash_password(req.password),
        name=req.name,
        dob=req.dob,
        gender=req.gender,
    )
    db.add(user)
    await db.flush()  # Get the user.id

    # Create empty personality profile
    profile = PersonalityProfile(user_id=user.id)
    db.add(profile)

    # Create empty user summary
    summary = UserSummary(user_id=user.id, summary_text="")
    db.add(summary)

    await db.commit()
    await db.refresh(user)

    tokens = create_token_pair(user.id, user.is_admin)

    return {
        "user": UserBasic.model_validate(user),
        "tokens": TokenResponse(**tokens),
    }


@router.post("/login")
async def login(
    req: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """Login with email and password."""
    result = await db.execute(
        select(User).where(User.email == req.email)
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    tokens = create_token_pair(user.id, user.is_admin)

    return {
        "user": UserBasic.model_validate(user),
        "tokens": TokenResponse(**tokens),
    }


@router.post("/refresh")
async def refresh_token(
    req: RefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    """Refresh an expired access token using a valid refresh token."""
    try:
        payload = decode_token(req.refresh_token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    user_id = int(payload["sub"])
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    tokens = create_token_pair(user.id, user.is_admin)
    return TokenResponse(**tokens)
