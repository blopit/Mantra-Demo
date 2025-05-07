"""
Integration tests for Google integration wrapper endpoints.
"""

import pytest
import pytest_asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
import logging
from datetime import datetime
from starlette.middleware.sessions import SessionMiddleware
import json
import base64
import itsdangerous
import os

from src.models.google_integration import GoogleIntegration
from src.routes.google_integration_wrapper import router as google_integration_router
from src.utils.database import get_db
from src.adapters.database.postgres import PostgresAdapter
from src.models.base import Base

# Disable logging for tests
logging.getLogger("src.routes.google_integration_wrapper").setLevel(logging.ERROR)

# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Test secret key
SECRET_KEY = "test_secret"

@pytest_asyncio.fixture
async def db_engine():
    """Create a test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=True,
        future=True
    )

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Drop tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest_asyncio.fixture
async def db_session(db_engine):
    """Create a test database session."""
    # Create async session factory
    async_session = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with async_session() as session:
        yield session

@pytest_asyncio.fixture
async def app(db_session):
    """Create a test FastAPI application."""
    app = FastAPI()
    
    # Add session middleware
    app.add_middleware(
        SessionMiddleware,
        secret_key=SECRET_KEY,
        session_cookie="session"
    )

    # Override get_db dependency
    async def get_test_db():
        try:
            yield db_session
        finally:
            await db_session.close()

    app.dependency_overrides[get_db] = get_test_db

    # Mount router with both prefixes to test prefix handling
    app.include_router(google_integration_router, prefix="/api/google-integrations")
    app.include_router(google_integration_router, prefix="/api/google/integrations")

    return app

@pytest.fixture
def client(app):
    """Create a test client."""
    return TestClient(app)

def create_session_cookie(data: dict) -> str:
    """Create a signed session cookie."""
    signer = itsdangerous.URLSafeSerializer(SECRET_KEY)
    return signer.dumps(data)

@pytest.fixture
def test_user():
    """Create a test user."""
    return {
        "id": "test_user_id",
        "email": "test@example.com",
        "name": "Test User"
    }

@pytest.mark.asyncio
async def test_router_prefix_handling(client):
    """Test that router prefixes are handled correctly."""
    # Both endpoints should work and point to the same handler
    response1 = client.get("/api/google-integrations/status")
    assert response1.status_code == 401  # Unauthorized without session

    response2 = client.get("/api/google/integrations/status")
    assert response2.status_code == 401  # Unauthorized without session

@pytest.mark.asyncio
async def test_get_integration_status_not_logged_in(client):
    """Test get_integration_status when user is not logged in."""
    response = client.get("/api/google-integrations/status")
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"

@pytest.mark.asyncio
async def test_get_integration_status_no_integration(client, test_user):
    """Test get_integration_status when user has no integration."""
    # Set up session with test user
    session_data = {"user": test_user}
    client.cookies["session"] = create_session_cookie(session_data)

    response = client.get("/api/google-integrations/status")
    assert response.status_code == 404
    assert response.json()["detail"] == "Google integration not found"

@pytest.mark.asyncio
async def test_get_integration_status_with_integration(client, test_user, db_session):
    """Test get_integration_status when user has an active integration."""
    # Create test integration
    integration = GoogleIntegration(
        id="test_integration_id",
        user_id=test_user["id"],
        google_account_id="test_account_id",
        email="test@example.com",
        is_active=True,
        status="connected",
        created_at=datetime.utcnow()
    )
    db_session.add(integration)
    await db_session.commit()

    # Set up session with test user
    session_data = {"user": test_user}
    client.cookies["session"] = create_session_cookie(session_data)

    response = client.get("/api/google-integrations/status")
    assert response.status_code == 200
    data = response.json()
    assert data["is_active"] is True
    assert data["status"] == "connected"

@pytest.mark.asyncio
async def test_get_integration_status_error_handling(client, test_user):
    """Test error handling in get_integration_status."""
    # Set up session with invalid user data to trigger error
    session_data = {"user": {"id": "invalid_id", "email": "invalid@email.com"}}
    client.cookies["session"] = create_session_cookie(session_data)

    response = client.get("/api/google-integrations/status")
    assert response.status_code == 404
    assert response.json()["detail"] == "Google integration not found" 