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
from src.models.users import Users
from src.models.mantra import Mantra, MantraInstallation
from src.main import app as main_app
from src.routes.mantra import get_test_session
from unittest.mock import patch

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
    
    # Create all tables
    Base.metadata.drop_all(bind=engine)  # Drop all tables first
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
def app(db_session, test_user):
    """Create test FastAPI app."""
    # Use the main app instance
    app = main_app
    
    # Override the database dependency
    app.dependency_overrides[get_db] = override_get_db(db_session)
    
    # Override the test session dependency
    def override_test_session():
        return {"user": {
            "id": test_user.id,
            "email": test_user.email,
            "name": test_user.name
        }}
    app.dependency_overrides[get_test_session] = override_test_session
    
    return app

@pytest.fixture(scope="function")
def client(app):
    """Get test client."""
    return TestClient(app)

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
def test_user(test_db):
    """Create a test user."""
    user = User(
        id=str(uuid.uuid4()),
        email="test@example.com",
        hashed_password="test_hashed_password"
    )
    test_db.add(user)
    test_db.commit()
    return user

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
