"""
Test configuration and fixtures for integration tests.
"""

import os
import pytest
import pytest_asyncio
from typing import Generator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from src.models.base import Base
from src.models.users import Users
from src.models.mantra import Mantra, MantraInstallation
from src.models.google_auth import GoogleAuth
from src.models.google_integration import GoogleIntegration
from datetime import datetime
from sqlalchemy import select, and_

# Test database URL - use in-memory SQLite
TEST_DATABASE_URL = "sqlite+aiosqlite://"

# Test N8N configuration
os.environ["N8N_API_URL"] = "http://localhost:5678"
os.environ["N8N_API_KEY"] = "test_api_key"
os.environ["N8N_API_TIMEOUT"] = "5.0"
os.environ["N8N_MAX_RETRIES"] = "3"
os.environ["N8N_RETRY_DELAY"] = "0.1"

@pytest_asyncio.fixture(scope="session")
async def engine():
    """Create test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=NullPool,
        echo=False
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()

@pytest_asyncio.fixture
async def db_session(engine) -> AsyncSession:
    """Create a test database session."""
    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False
    )
    
    async with session_factory() as session:
        yield session

def override_get_db(db_session: AsyncSession):
    """Create a callable dependency override for get_db."""
    async def _get_test_db():
        try:
            yield db_session
        finally:
            pass  # Don't close the session here, it's handled by the fixture
    return _get_test_db

@pytest_asyncio.fixture
async def test_user(db_session):
    """Create a test user."""
    # Check if user already exists
    stmt = select(Users).where(Users.email == "test@example.com")
    result = await db_session.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        user = Users(
            id="test_user_id",
            email="test@example.com",
            name="Test User",
            profile_picture="https://example.com/picture.jpg",
            is_active=True
        )
        db_session.add(user)
        await db_session.commit()
    
    return user

@pytest_asyncio.fixture
async def test_google_integration(test_user, db_session):
    """Create a test Google integration."""
    # Check if integration already exists
    stmt = select(GoogleIntegration).where(
        and_(
            GoogleIntegration.user_id == test_user.id,
            GoogleIntegration.email == test_user.email
        )
    )
    result = await db_session.execute(stmt)
    integration = result.scalar_one_or_none()
    
    if not integration:
        integration = GoogleIntegration(
            id="test_integration_id",
            user_id=test_user.id,
            google_account_id="test_account_id",
            email=test_user.email,
            service_name="google",
            is_active=True,
            status="connected",
            access_token="test_access_token",
            refresh_token="test_refresh_token",
            expires_at=datetime.utcnow(),
            scopes="email profile",
            settings="{}"
        )
        db_session.add(integration)
        await db_session.commit()
    
    return integration

@pytest_asyncio.fixture
async def test_google_auth(test_user, db_session):
    """Create a test Google auth record."""
    # Check if auth record already exists
    stmt = select(GoogleAuth).where(GoogleAuth.user_id == test_user.id)
    result = await db_session.execute(stmt)
    auth = result.scalar_one_or_none()
    
    if not auth:
        auth = GoogleAuth(
            user_id=test_user.id,
            email=test_user.email,
            access_token="test_access_token",
            refresh_token="test_refresh_token",
            token_expiry=datetime.utcnow()
        )
        db_session.add(auth)
        await db_session.commit()
    
    return auth

@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch):
    """Mock environment variables for tests."""
    monkeypatch.setenv("N8N_API_URL", "http://localhost:5678")
    monkeypatch.setenv("N8N_API_KEY", "test_api_key")
    monkeypatch.setenv("N8N_API_TIMEOUT", "5.0")
    monkeypatch.setenv("N8N_MAX_RETRIES", "3")
    monkeypatch.setenv("N8N_RETRY_DELAY", "0.1") 