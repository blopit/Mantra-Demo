"""
Integration tests for Google authentication flow.
"""

import os
import json
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from fastapi import Request
from google.oauth2.credentials import Credentials
from datetime import datetime, timedelta
import uuid
from sqlalchemy.orm import Session

# Import the router and models
from src.models.google_integration import GoogleIntegration
from src.models.users import Users
from src.routes.google_auth_consolidated import get_current_user

# Default scopes for Google OAuth
DEFAULT_SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/userinfo.email"
]

class AsyncMockSession:
    def __init__(self, data=None):
        self._data = data or {}

    def get(self, key, default=None):
        return self._data.get(key, default)

    def pop(self, key, default=None):
        return self._data.pop(key, default)

    def __getitem__(self, key):
        return self._data[key]

@pytest.fixture
def mock_session():
    """Mock session data."""
    def _mock_session(data=None):
        mock_request = AsyncMock(spec=Request)
        mock_request.session = AsyncMockSession(data)
        return mock_request
    return _mock_session

@pytest.fixture(autouse=True)
def setup_db(db_session):
    """Set up test database."""
    # Clear any existing data
    db_session.query(GoogleIntegration).delete()
    db_session.query(Users).delete()
    db_session.commit()
    yield
    # Clean up after test
    db_session.query(GoogleIntegration).delete()
    db_session.query(Users).delete()
    db_session.commit()

@pytest.fixture
def test_user(db_session):
    """Create a test user."""
    user = Users(
        id="test_user_id",
        email="test@example.com",
        name="Test User",
        profile_picture="https://test.picture"
    )
    db_session.add(user)
    db_session.commit()
    return user

@pytest.fixture
def mock_get_token():
    """Mock get_google_token function."""
    async def mock_func(code):
        return {
            "access_token": "test_token",
            "refresh_token": "test_refresh",
            "expires_in": 3600,
            "scope": " ".join(DEFAULT_SCOPES),
            "token_type": "Bearer",
            "id_token": "test_id_token"
        }
    return mock_func

@pytest.fixture
def mock_get_user_info():
    """Mock get_google_user_info function."""
    async def mock_func(token):
        return {
            "sub": "123456789012345678901",
            "email": "test@example.com",
            "name": "Test User",
            "picture": "https://test.picture"
        }
    return mock_func

def test_auth_url_success(client):
    """Test successful auth URL generation."""
    response = client.get("/api/google/auth")
    assert response.status_code == 200
    assert "auth_url" in response.json()

def test_callback_success(
    client: TestClient,
    test_db: Session,
    test_user,
    mock_get_google_token,
    mock_get_google_user_info
):
    """Test successful OAuth callback."""
    # Setup
    oauth_state = str(uuid.uuid4())
    client.set_cookie("oauth_state", oauth_state)
    client.set_cookie("user_id", test_user.id)

    # Mock responses
    mock_get_google_token.return_value = {
        "access_token": "test_access_token",
        "refresh_token": "test_refresh_token",
        "expires_in": 3600
    }
    mock_get_google_user_info.return_value = {
        "id": "test_google_id",
        "email": "test@gmail.com"
    }

    # Test
    response = client.get(
        f"/google/callback?state={oauth_state}&code=test_code"
    )

    assert response.status_code == 200
    assert response.json()["message"] == "Google account connected successfully"

    # Verify database
    integration = test_db.query(GoogleIntegration).filter_by(user_id=test_user.id).first()
    assert integration is not None
    assert integration.google_account_id == "test_google_id"
    assert integration.email == "test@gmail.com"
    assert integration.status == "connected"
    assert integration.access_token == "test_access_token"
    assert integration.refresh_token == "test_refresh_token"

def test_callback_invalid_state(
    client: TestClient,
    test_db: Session,
    test_user
):
    """Test callback with invalid state."""
    # Setup
    oauth_state = str(uuid.uuid4())
    client.set_cookie("oauth_state", oauth_state)
    client.set_cookie("user_id", test_user.id)

    # Test with different state
    response = client.get(
        f"/google/callback?state=invalid_state&code=test_code"
    )

    assert response.status_code == 400
    assert "Invalid state parameter" in response.json()["detail"]

def test_status_connected(client, test_user, db_session, mock_session):
    """Test connection status when user is connected."""
    integration = GoogleIntegration(
        id=str(uuid.uuid4()),
        user_id=test_user.id,
        google_account_id="123456789012345678901",
        email=test_user.email,
        service_name="google",
        is_active=True,
        status="active",
        access_token="test_token",
        refresh_token="test_refresh",
        expires_at=datetime.utcnow() + timedelta(hours=1)
    )
    db_session.add(integration)
    db_session.commit()

    mock_req = mock_session({
        "user": {
            "id": test_user.id,
            "email": test_user.email,
            "name": test_user.name,
            "picture": test_user.profile_picture
        }
    })

    with patch("fastapi.Request", return_value=mock_req):
        response = client.get("/api/google/status")
        assert response.status_code == 200
        data = response.json()
        assert data["connected"] is True
        assert data["email"] == test_user.email

def test_disconnect(
    client: TestClient,
    test_db: Session,
    test_user,
    mock_revoke_token
):
    """Test disconnecting Google integration."""
    # Setup
    integration = GoogleIntegration(
        id=str(uuid.uuid4()),
        user_id=test_user.id,
        google_account_id="test_google_id",
        email="test@gmail.com",
        status="connected",
        access_token="test_access_token",
        refresh_token="test_refresh_token"
    )
    test_db.add(integration)
    test_db.commit()

    # Mock token revocation
    mock_revoke_token.return_value = True

    # Test
    response = client.post("/google/disconnect")

    assert response.status_code == 200
    assert response.json()["message"] == "Google account disconnected successfully"

    # Verify database
    integration = test_db.query(GoogleIntegration).filter_by(user_id=test_user.id).first()
    assert integration.status == "disconnected"
    assert integration.disconnected_at is not None
