"""
Pytest configuration and fixtures.
"""

import os
import pytest
from httpx import AsyncClient, ASGITransport
from typing import AsyncGenerator

# Set test environment before importing the app
os.environ["APP_ENV"] = "testing"
os.environ["SECRET_KEY"] = "test_secret_key_for_jwt_tokens_1234567890"

from app.main import app


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Provides an async HTTP client for the FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
