"""
Pytest configuration and fixtures for testing.

This module provides shared fixtures and configuration for all tests.
"""

import os
import sys
import json
import pytest
import pytest_asyncio
import uuid
from pathlib import Path
from sqlalchemy import create_engine, TypeDecorator, String
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware
from fastapi.middleware.cors import CORSMiddleware
from src.models.base import Base
from src.models.users import Users
from src.models.mantra import Mantra, MantraInstallation
from src.main import app as main_app
from src.routes.mantra import get_test_session, get_n8n_service
from unittest.mock import patch, MagicMock, AsyncMock
from google.oauth2.credentials import Credentials
from datetime import datetime
import asyncio

# Add the project root directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import project modules
from src.utils.google_credentials import (
    get_credentials_from_database_url,
    store_credentials_in_database_url,
    clear_credentials_from_database_url
)
from src.custom_routes.google.auth import router as google_auth_router
from src.routes.mantra import router as mantra_router
from src.utils.database import get_db, SQLiteUUID
from src.utils.config import Settings
from src.services.n8n_service import N8nService
from tests.fixtures.n8n_service import mock_n8n_service

class SQLiteUUID(TypeDecorator):
    """Platform-independent UUID type.
    Uses String(32) as underlying type for SQLite.
    """

    impl = String
    cache_ok = True

    def __init__(self):
        super().__init__(length=32)

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        return str(value).replace('-', '')

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        return uuid.UUID(value)

# Override UUID type for SQLite
from sqlalchemy.dialects import sqlite
sqlite.base.ischema_names['uuid'] = SQLiteUUID

# Set testing environment
os.environ["TESTING"] = "true"

# Set up test database
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

settings = Settings()

engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=True,
)

async_session = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

@pytest_asyncio.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture(scope="session")
async def setup_database():
    """Set up the test database."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture
async def db_session(setup_database) -> AsyncSession:
    """Create a fresh database session for a test."""
    async with async_session() as session:
        yield session
        await session.rollback()
        await session.close()

@pytest.fixture
def test_app() -> FastAPI:
    """Create a new test application instance."""
    # Create a new FastAPI instance
    app = FastAPI()
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"]
    )
    
    # Add session middleware
    app.add_middleware(
        SessionMiddleware,
        secret_key="test_secret_key",
        session_cookie="session"
    )
    
    # Include routers
    app.include_router(google_auth_router)
    app.include_router(mantra_router)
    
    return app

@pytest.fixture
def client(test_app, test_user, db_session, mock_n8n_service) -> TestClient:
    """Create a test client with authentication."""
    # Override the database dependency
    test_app.dependency_overrides[get_db] = override_get_db(db_session)
    
    # Override the test session dependency
    def override_test_session():
        return {
            "user": {
                "id": test_user.id,
                "email": test_user.email,
                "name": test_user.name
            }
        }
    
    # Override the N8N service dependency
    def override_get_n8n_service():
        return mock_n8n_service
    
    test_app.dependency_overrides[get_test_session] = override_test_session
    test_app.dependency_overrides[get_n8n_service] = override_get_n8n_service
    
    # Create test client with base_url to ensure cookies are properly handled
    client = TestClient(test_app, base_url="http://testserver")
    
    return client

@pytest.fixture
def test_settings() -> Settings:
    """Get test settings."""
    return settings

def override_get_db(db_session):
    """Create a callable dependency override for get_db."""
    async def _get_test_db():
        yield db_session
    return _get_test_db

@pytest_asyncio.fixture
async def test_user(db_session):
    """Create a test user."""
    user_id = str(uuid.uuid4())
    user = Users(
        id=user_id,
        email=f"test_{user_id}@example.com",  # Unique email per test
        name="Test User",
        is_active=True  # Ensure user is active by default
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user

@pytest.fixture
def mock_env_empty():
    """Fixture to provide an empty environment."""
    old_environ = dict(os.environ)
    os.environ.clear()
    yield
    os.environ.clear()
    os.environ.update(old_environ)


@pytest.fixture
def mock_env_with_database_url():
    """Fixture to provide an environment with DATABASE_URL."""
    old_environ = dict(os.environ)
    os.environ.clear()
    
    # Create mock credentials
    mock_credentials = {
        "access_token": "mock_access_token",
        "refresh_token": "mock_refresh_token",
        "token_uri": "https://oauth2.googleapis.com/token",
        "client_id": "mock_client_id.apps.googleusercontent.com",
        "client_secret": "mock_client_secret",
        "scopes": ["https://www.googleapis.com/auth/userinfo.email"],
        "expiry": "2023-12-31T23:59:59Z",
        "user_info": {
            "email": "test@example.com",
            "name": "Test User",
            "picture": "https://example.com/picture.jpg",
            "id": "123456789"
        }
    }
    
    # Set DATABASE_URL
    os.environ["DATABASE_URL"] = json.dumps(mock_credentials)
    
    yield mock_credentials
    
    os.environ.clear()
    os.environ.update(old_environ)


@pytest.fixture
def mock_env_with_google_credentials():
    """Fixture to provide an environment with Google credentials."""
    old_environ = dict(os.environ)
    os.environ.clear()
    
    # Set Google credentials
    os.environ["GOOGLE_CLIENT_ID"] = "test_client_id"
    os.environ["GOOGLE_CLIENT_SECRET"] = "test_client_secret"
    os.environ["GOOGLE_REDIRECT_URI"] = "http://localhost:8000/auth/google/store"
    os.environ["GOOGLE_AUTH_STATE"] = "test_state"
    os.environ["GOOGLE_TOKEN_URI"] = "https://oauth2.googleapis.com/token"
    os.environ["GOOGLE_AUTH_URI"] = "https://accounts.google.com/o/oauth2/auth"
    
    yield
    
    os.environ.clear()
    os.environ.update(old_environ)


@pytest.fixture
def mock_credentials():
    """Fixture to provide mock Google credentials."""
    return {
        "access_token": "mock_access_token",
        "refresh_token": "mock_refresh_token",
        "token_uri": "https://oauth2.googleapis.com/token",
        "client_id": "mock_client_id.apps.googleusercontent.com",
        "client_secret": "mock_client_secret",
        "scopes": ["https://www.googleapis.com/auth/userinfo.email"],
        "expiry": "2023-12-31T23:59:59Z"
    }


@pytest.fixture
def mock_user_info():
    """Fixture to provide mock user info."""
    return {
        "email": "test@example.com",
        "name": "Test User",
        "picture": "https://example.com/picture.jpg",
        "sub": "123456789012345678901"  # 21-digit Google user ID
    }

@pytest.fixture
def mock_get_google_token():
    """Mock the Google token endpoint response."""
    with patch("src.routes.google_auth_consolidated.get_google_token") as mock:
        yield mock

@pytest.fixture
def mock_get_google_user_info():
    """Mock the Google user info endpoint response."""
    with patch("src.routes.google_auth_consolidated.get_google_user_info") as mock:
        yield mock

@pytest.fixture
def mock_revoke_token():
    """Mock the Google token revocation endpoint."""
    with patch("src.routes.google_auth_consolidated.revoke_google_token") as mock:
        yield mock

@pytest.fixture
def test_db():
    """Create a test database session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(engine)

@pytest.fixture(autouse=True)
def setup_test_environment():
    """Set up test environment variables."""
    # Set up test environment variables
    os.environ["N8N_API_URL"] = "http://localhost:5678/api/v1"
    os.environ["N8N_API_KEY"] = "test-api-key"
    os.environ["N8N_WEBHOOK_URL"] = "http://localhost:5678"
    os.environ["ENVIRONMENT"] = "test"
    
    # Mock N8N service
    with patch("src.services.n8n_service.N8nService") as mock:
        instance = mock.return_value
        # Mock successful workflow creation
        async def create_workflow(*args, **kwargs):
            return 123
        instance.create_workflow = AsyncMock(side_effect=create_workflow)
        
        # Mock successful workflow activation
        async def activate_workflow(*args, **kwargs):
            return True
        instance.activate_workflow = AsyncMock(side_effect=activate_workflow)
        
        # Mock successful workflow deactivation
        async def deactivate_workflow(*args, **kwargs):
            return True
        instance.deactivate_workflow = AsyncMock(side_effect=deactivate_workflow)
        
        # Mock successful workflow deletion
        async def delete_workflow(*args, **kwargs):
            return True
        instance.delete_workflow = AsyncMock(side_effect=delete_workflow)
        
        # Mock successful workflow execution
        async def execute_workflow(*args, **kwargs):
            return {
                "success": True,
                "result": {
                    "execution_id": "test-execution-id",
                    "status": "success",
                    "data": {"output": "test output"}
                }
            }
        instance.execute_workflow = AsyncMock(side_effect=execute_workflow)
        
        # Mock successful workflow parsing
        async def parse_workflow(*args, **kwargs):
            return {"nodes": [], "connections": {}}
        instance.parse_workflow = AsyncMock(side_effect=parse_workflow)
        
        yield instance
    
    # Clean up
    os.environ.pop("N8N_API_URL", None)
    os.environ.pop("N8N_API_KEY", None)
    os.environ.pop("N8N_WEBHOOK_URL", None)
    os.environ.pop("ENVIRONMENT", None)

@pytest.fixture
def mock_google_auth(monkeypatch):
    """Mock Google OAuth flow."""
    # Mock Flow class
    mock_flow = MagicMock()
    mock_flow_instance = mock_flow.from_client_config.return_value
    mock_flow_instance.credentials = Credentials(
        token="test_token",
        refresh_token="test_refresh_token",
        token_uri="https://oauth2.googleapis.com/token",
        client_id="test_client_id",
        client_secret="test_client_secret",
        scopes=["openid", "https://www.googleapis.com/auth/userinfo.profile", "https://www.googleapis.com/auth/userinfo.email"]
    )
    mock_flow_instance.credentials.expiry = datetime.now()
    mock_flow_instance.authorization_url.return_value = ("https://test.url", "test_state")
    mock_flow_instance.fetch_token.return_value = {
        "access_token": "test_token",
        "refresh_token": "test_refresh_token",
        "expires_in": 3600
    }

    # Mock userinfo service
    mock_service = MagicMock()
    mock_service_instance = mock_service.return_value
    mock_userinfo = mock_service_instance.userinfo.return_value
    mock_userinfo.get.return_value.execute.return_value = {
        "email": "test@example.com",
        "name": "Test User",
        "picture": "https://test.picture.url",
        "sub": "test_user_id"
    }

    # Patch the required functions
    monkeypatch.setattr("src.custom_routes.google.auth.Flow", mock_flow)
    monkeypatch.setattr("src.custom_routes.google.auth.build", lambda *args, **kwargs: mock_service_instance)

    return mock_flow_instance
