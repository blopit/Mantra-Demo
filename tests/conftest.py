"""
Pytest configuration and fixtures for testing.

This module provides shared fixtures and configuration for all tests.
"""

import os
import sys
import json
import pytest
import uuid
from pathlib import Path
from sqlalchemy import create_engine, TypeDecorator, String
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware
from fastapi.middleware.cors import CORSMiddleware
from src.models.base import Base

# Add the project root directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import project modules
from src.utils.google_credentials import (
    get_credentials_from_database_url,
    store_credentials_in_database_url,
    clear_credentials_from_database_url
)
from src.custom_routes.google.auth import router as google_auth_router
from src.utils.database import get_db, SQLiteUUID

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
TEST_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture(scope="session")
def engine():
    """Create test database engine."""
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    return engine

@pytest.fixture(scope="session")
def TestingSessionLocal(engine):
    """Create test database session factory."""
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture
def db_session(TestingSessionLocal):
    """Get test database session."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()

def override_get_db(db_session):
    """Create a callable dependency override for get_db."""
    def _get_test_db():
        try:
            yield db_session
        finally:
            pass  # Session is handled by the db_session fixture
    return _get_test_db

@pytest.fixture(scope="function")
def app():
    """Create test FastAPI app."""
    app = FastAPI()
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add session middleware
    app.add_middleware(SessionMiddleware, secret_key="test_secret")
    
    # Add root route
    @app.get("/")
    async def root():
        return {"message": "Hello World"}
    
    # Include Google auth router
    app.include_router(google_auth_router)
    
    return app

@pytest.fixture(scope="function")
def client(app, db_session):
    """Get test client with overridden database dependency."""
    app.dependency_overrides[get_db] = override_get_db(db_session)
    client = TestClient(app, follow_redirects=False)
    yield client
    app.dependency_overrides.clear()

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
    os.environ["GOOGLE_CLIENT_ID"] = "mock_client_id.apps.googleusercontent.com"
    os.environ["GOOGLE_CLIENT_SECRET"] = "mock_client_secret"
    os.environ["GOOGLE_REDIRECT_URI"] = "http://localhost:8000/auth/google/callback"
    
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
        "sub": "123456789"
    }
