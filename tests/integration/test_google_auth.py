"""
Integration tests for Google authentication flow.
"""

import os
import json
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from google.oauth2.credentials import Credentials

# Import the router and models
from src.models.google_auth import GoogleAuth
from src.models.users import Users

@pytest.fixture(autouse=True)
def setup_db(db_session):
    """Set up test database."""
    # Clear any existing data
    db_session.query(GoogleAuth).delete()
    db_session.query(Users).delete()
    db_session.commit()
    yield
    # Clean up after test
    db_session.query(GoogleAuth).delete()
    db_session.query(Users).delete()
    db_session.commit()

@pytest.fixture
def mock_flow():
    """Mock Google OAuth flow."""
    mock = MagicMock()
    mock.authorization_url.return_value = ("https://test.url", "test_state")
    
    # Create mock credentials
    mock_creds = MagicMock(spec=Credentials)
    mock_creds.token = "test_token"
    mock_creds.refresh_token = "test_refresh"
    mock_creds.token_uri = "https://test.uri"
    mock_creds.client_id = "test_client_id"
    mock_creds.client_secret = "test_client_secret"
    mock_creds.scopes = ["test_scope"]
    
    mock.fetch_token.return_value = {
        "access_token": "test_token",
        "refresh_token": "test_refresh",
        "token_uri": "https://test.uri",
        "client_id": "test_client_id",
        "client_secret": "test_client_secret",
        "scopes": ["test_scope"]
    }
    mock.credentials = mock_creds
    return mock

@pytest.fixture
def mock_service():
    """Mock Google service."""
    mock = MagicMock()
    mock.userinfo().get().execute.return_value = {
        "email": "test@example.com",
        "name": "Test User",
        "picture": "https://test.picture"
    }
    return mock

def test_auth_url_error(client, mock_flow):
    """Test error handling in auth URL generation."""
    mock_flow.authorization_url.side_effect = Exception("Test error")
    with patch("src.custom_routes.google.auth.build_google_oauth", return_value=mock_flow):
        response = client.get("/auth/google/url")
        assert response.status_code == 500
        assert response.json()["detail"] == "Test error"

def test_auth_url_success(client, mock_flow):
    """Test successful auth URL generation."""
    with patch("src.custom_routes.google.auth.build_google_oauth", return_value=mock_flow):
        response = client.get("/auth/google/url")
        assert response.status_code == 200
        assert response.json()["url"] == "https://test.url"

def test_callback_success(client, mock_flow, mock_service, db_session):
    """Test successful OAuth callback."""
    with patch("src.custom_routes.google.auth.build_google_oauth", return_value=mock_flow), \
         patch("src.custom_routes.google.auth.build", return_value=mock_service):
        response = client.get("/auth/google/callback?code=test_code&state=test_state")
        assert response.status_code == 303
        assert response.headers["location"] == "/auth/google/store"

        # Verify user was created
        user = db_session.query(Users).filter_by(email="test@example.com").first()
        assert user is not None
        assert user.name == "Test User"
        assert user.profile_picture == "https://test.picture"

def test_store_in_db_url(client, db_session):
    """Test storing auth data in database."""
    # Create test user first
    user = Users(
        email="test@example.com",
        name="Test User",
        profile_picture="https://test.picture"
    )
    db_session.add(user)
    db_session.flush()

    # Create test auth
    auth = GoogleAuth(
        user_id=user.id,
        access_token="test_token",
        refresh_token="test_refresh"
    )
    db_session.add(auth)
    db_session.commit()

    # Test the store endpoint
    response = client.get("/auth/google/store")
    assert response.status_code == 303
    assert response.headers["location"] == "/"

def test_status_connected(client, db_session):
    """Test connection status when user is connected."""
    # Create test user
    user = Users(
        email="test@example.com",
        name="Test User",
        profile_picture="https://test.picture"
    )
    db_session.add(user)
    db_session.flush()

    # Create test auth
    auth = GoogleAuth(
        user_id=user.id,
        access_token="test_token",
        refresh_token="test_refresh"
    )
    db_session.add(auth)
    db_session.commit()

    response = client.get("/auth/google/status")
    assert response.status_code == 200
    data = response.json()
    assert data["connected"] is True
    assert data["user"]["email"] == "test@example.com"

def test_status_not_connected(client):
    """Test connection status when user is not connected."""
    response = client.get("/auth/google/status")
    assert response.status_code == 200
    data = response.json()
    assert data["connected"] is False
    assert data["user"] is None

def test_disconnect(client, db_session):
    """Test disconnecting Google account."""
    # Create test user
    user = Users(
        email="test@example.com",
        name="Test User",
        profile_picture="https://test.picture"
    )
    db_session.add(user)
    db_session.flush()

    # Create test auth
    auth = GoogleAuth(
        user_id=user.id,
        access_token="test_token",
        refresh_token="test_refresh"
    )
    db_session.add(auth)
    db_session.commit()

    response = client.post("/auth/google/disconnect")
    assert response.status_code == 200
    assert response.json()["message"] == "Successfully disconnected from Google"

    # Verify auth record was deleted
    auth = db_session.query(GoogleAuth).filter_by(user_id=user.id).first()
    assert auth is None
