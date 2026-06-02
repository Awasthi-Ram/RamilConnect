"""Health check endpoint."""

from fastapi import APIRouter

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check():
    """Simple health check endpoint."""
    return {"status": "ok", "app": "RamilConnect", "version": "1.0.0"}
