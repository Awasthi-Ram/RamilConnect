"""
Admin Dashboard Web Routes — server-side rendered pages.

Uses Jinja2 templates with session-based auth via cookies.
These routes serve the admin web UI at /admin/*.
"""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, desc, func as sqlfunc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.companion import CompanionMessage, CompanionSession
from app.models.personality import PersonalityProfile
from app.models.match import Match
from app.models.admin import AdminConfig
from app.utils.security import verify_password, create_access_token, decode_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin Dashboard"])

# Templates directory
TEMPLATE_DIR = Path(__file__).parent.parent.parent / "admin_dashboard" / "templates"
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))

# Cookie name for admin session
ADMIN_COOKIE = "rc_admin_token"


# ── Auth Helpers ─────────────────────────────────────────────

def _get_admin_user_id(request: Request) -> int | None:
    """Extract admin user ID from cookie."""
    token = request.cookies.get(ADMIN_COOKIE)
    if not token:
        return None
    try:
        payload = decode_token(token)
        if payload.get("is_admin"):
            return int(payload["sub"])
    except Exception:
        pass
    return None


async def _require_admin(request: Request, db: AsyncSession) -> User:
    """Verify admin auth or redirect to login."""
    user_id = _get_admin_user_id(request)
    if not user_id:
        raise HTTPException(status_code=303, headers={"Location": "/admin/login"})

    result = await db.execute(select(User).where(User.id == user_id, User.is_admin == True))
    admin = result.scalar_one_or_none()
    if not admin:
        raise HTTPException(status_code=303, headers={"Location": "/admin/login"})

    return admin


# ── Login / Logout ───────────────────────────────────────────

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Render admin login page."""
    return templates.TemplateResponse("login.html", {"request": request, "error": None})


@router.post("/login", response_class=HTMLResponse)
async def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    """Handle admin login form submission."""
    result = await db.execute(
        select(User).where(User.email == email, User.is_admin == True)
    )
    admin = result.scalar_one_or_none()

    if not admin or not verify_password(password, admin.password_hash):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Invalid email or password"},
        )

    # Create admin token and set cookie
    token = create_access_token(admin.id, extra_claims={"is_admin": True})
    response = RedirectResponse(url="/admin", status_code=303)
    response.set_cookie(
        ADMIN_COOKIE,
        token,
        httponly=True,
        max_age=60 * 60 * 24,  # 24 hours
        samesite="lax",
    )
    return response


@router.get("/logout")
async def logout():
    """Logout and clear admin cookie."""
    response = RedirectResponse(url="/admin/login", status_code=303)
    response.delete_cookie(ADMIN_COOKIE)
    return response


# ── Dashboard ────────────────────────────────────────────────

@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Main admin dashboard."""
    admin = await _require_admin(request, db)

    # Aggregate stats
    total_users = (await db.execute(select(sqlfunc.count()).select_from(User))).scalar() or 0
    total_messages = (await db.execute(select(sqlfunc.count()).select_from(CompanionMessage))).scalar() or 0
    active_sessions = (await db.execute(
        select(sqlfunc.count()).select_from(CompanionSession).where(CompanionSession.is_active == True)
    )).scalar() or 0
    personality_profiles = (await db.execute(
        select(sqlfunc.count()).select_from(PersonalityProfile).where(PersonalityProfile.confidence_score > 0.1)
    )).scalar() or 0
    total_matches = (await db.execute(select(sqlfunc.count()).select_from(Match))).scalar() or 0

    # Recent users
    result = await db.execute(
        select(User).order_by(desc(User.created_at)).limit(10)
    )
    recent_users = [
        {
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "companion_persona": u.companion_persona,
            "onboarding_complete": u.onboarding_complete,
            "created_at": u.created_at.isoformat(),
        }
        for u in result.scalars().all()
    ]

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "active_page": "dashboard",
        "stats": {
            "total_users": total_users,
            "total_messages": total_messages,
            "active_sessions": active_sessions,
            "personality_profiles": personality_profiles,
            "total_matches": total_matches,
        },
        "recent_users": recent_users,
    })
