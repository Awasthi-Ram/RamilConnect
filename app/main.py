"""
RamilConnect — FastAPI Application Entry Point.

Sets up CORS, routes, lifespan, and admin dashboard mount.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.database import init_db, close_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Lifespan ─────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — startup and shutdown hooks."""
    settings = get_settings()
    logger.info(f"🚀 Starting {settings.app_name} ({settings.app_env})")

    # Initialize database (create tables if dev)
    if not settings.is_production:
        await init_db()
        logger.info("📦 Database tables created/verified")

    # Seed admin user if needed
    await _seed_admin()

    yield

    # Shutdown
    await close_db()
    logger.info("👋 Shutdown complete")


async def _seed_admin():
    """Create the default admin user if it doesn't exist."""
    from sqlalchemy import select
    from app.database import get_db_context
    from app.models.user import User
    from app.utils.security import hash_password

    settings = get_settings()

    async with get_db_context() as db:
        result = await db.execute(
            select(User).where(User.email == settings.admin_email)
        )
        admin = result.scalar_one_or_none()

        if not admin:
            admin = User(
                email=settings.admin_email,
                password_hash=hash_password(settings.admin_password),
                name="Admin",
                dob="1990-01-01",
                gender="other",
                is_admin=True,
                onboarding_complete=True,
                verified=True,
            )
            db.add(admin)
            await db.commit()
            logger.info(f"👤 Admin user seeded: {settings.admin_email}")
        else:
            logger.info(f"👤 Admin user exists: {settings.admin_email}")


# ── App Factory ──────────────────────────────────────────────

def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="RamilConnect API",
        description="Your AI Soulmate Companion — API Backend",
        version="1.0.0",
        docs_url="/api/docs" if not settings.is_production else None,
        redoc_url="/api/redoc" if not settings.is_production else None,
        lifespan=lifespan,
    )

    # ── CORS ─────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins + ["*"],  # Allow all in dev
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── API Routes ───────────────────────────────────────────
    from app.routes.health import router as health_router
    from app.routes.auth import router as auth_router
    from app.routes.user import router as user_router
    from app.routes.companion import router as companion_router
    from app.routes.admin import router as admin_router
    from app.routes.admin_dashboard import router as admin_dashboard_router

    app.include_router(health_router, prefix="/api")
    app.include_router(auth_router, prefix="/api")
    app.include_router(user_router, prefix="/api")
    app.include_router(companion_router, prefix="/api")
    app.include_router(admin_router, prefix="/api")
    app.include_router(admin_dashboard_router)  # Served at /admin

    # ── Root endpoint ────────────────────────────────────────
    @app.get("/")
    async def root():
        return {
            "app": "RamilConnect",
            "tagline": "Your AI Soulmate Companion",
            "version": "1.0.0",
            "api_docs": "/api/docs",
        }

    return app


# ── App Instance ─────────────────────────────────────────────
app = create_app()
