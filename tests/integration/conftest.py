"""
Test configuration and fixtures for integration tests.
"""

import os
import pytest
import pytest_asyncio
from typing import Generator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from src.models.base import Base
from src.models.users import Users
from src.models.mantra import Mantra, MantraInstallation
from src.models.google_auth import GoogleAuth
from src.models.google_integrations import GoogleIntegration
from src.models.contacts import Contact

# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"  # Use in-memory database for tests

# Test N8N configuration
os.environ["N8N_API_URL"] = "http://localhost:5678"
os.environ["N8N_API_KEY"] = "test_api_key"
os.environ["N8N_API_TIMEOUT"] = "5.0"
os.environ["N8N_MAX_RETRIES"] = "3"
os.environ["N8N_RETRY_DELAY"] = "0.1"

# Create async engine for tests
engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=True,
    poolclass=StaticPool,  # Use static pool for in-memory database
    connect_args={"check_same_thread": False}  # Allow multiple threads to use the same connection
)

# Create async session factory
TestingSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=True
)

@pytest_asyncio.fixture(scope="function", autouse=True)
async def setup_database():
    """Set up the test database.
    
    This fixture:
    1. Creates all tables before each test
    2. Provides the test with a clean database
    3. Drops all tables after the test
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    yield
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture
async def db_session() -> Generator:
    """Create a clean database session for a test.
    
    This fixture:
    1. Creates a new session
    2. Starts a transaction
    3. Yields the session
    4. Rolls back the transaction
    5. Closes the session
    """
    session = TestingSessionLocal()
    
    try:
        yield session
    finally:
        await session.close()

def override_get_db(db_session: AsyncSession):
    """Create a callable dependency override for get_db."""
    async def _get_test_db():
        try:
            yield db_session
        finally:
            pass  # Don't close the session here, it's handled by the fixture
    return _get_test_db

@pytest.fixture
def test_user() -> Users:
    """Create a test user."""
    return Users(
        id="test_user_id",
        email="test@example.com",
        name="Test User",
        is_active=True
    )

@pytest.fixture
def test_contact(test_user) -> Contact:
    """Create a test contact."""
    return Contact(
        id=1,
        user_id=test_user.id,
        email="contact@example.com",
        name="Test Contact",
        source="manual"
    )

@pytest.fixture
def test_google_auth(test_user) -> GoogleAuth:
    """Create a test Google auth."""
    return GoogleAuth(
        id=1,
        user_id=test_user.id,
        email="test@example.com",
        access_token="test_access_token",
        refresh_token="test_refresh_token"
    )

@pytest.fixture
def test_google_integration(test_user) -> GoogleIntegration:
    """Create a test Google integration."""
    return GoogleIntegration(
        id="test_integration_id",
        user_id=test_user.id,
        google_account_id="test_account_id",
        email="test@example.com",
        service_name="gmail",
        is_active=True,
        status="connected"
    )

@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch):
    """Mock environment variables for tests."""
    monkeypatch.setenv("N8N_API_URL", "http://localhost:5678")
    monkeypatch.setenv("N8N_API_KEY", "test_api_key")
    monkeypatch.setenv("N8N_API_TIMEOUT", "5.0")
    monkeypatch.setenv("N8N_MAX_RETRIES", "3")
    monkeypatch.setenv("N8N_RETRY_DELAY", "0.1") 