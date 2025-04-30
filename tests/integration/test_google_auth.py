"""
Integration tests for Google authentication endpoints.
"""

import os
import json
import pytest
import pytest_asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from fastapi import Request
from google.oauth2.credentials import Credentials
from datetime import datetime, timedelta
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from itsdangerous import URLSafeSerializer

# Import the router and models
from src.models.google_auth import GoogleAuth
from src.models.users import Users

@pytest.fixture
def mock_google_auth(monkeypatch):
    """Mock Google OAuth flow."""
    # Mock Flow class
    mock_flow = MagicMock()
    mock_flow_instance = MagicMock()
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

    # Mock fetch_token method
    def mock_fetch_token(code=None):
        mock_flow_instance.credentials = Credentials(
            token="test_token",
            refresh_token="test_refresh_token",
            token_uri="https://oauth2.googleapis.com/token",
            client_id="test_client_id",
            client_secret="test_client_secret",
            scopes=["openid", "https://www.googleapis.com/auth/userinfo.profile", "https://www.googleapis.com/auth/userinfo.email"]
        )
        mock_flow_instance.credentials.expiry = datetime.now()
        return {
            "access_token": "test_token",
            "refresh_token": "test_refresh_token",
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": "test_client_id",
            "client_secret": "test_client_secret",
            "scopes": ["openid", "https://www.googleapis.com/auth/userinfo.profile", "https://www.googleapis.com/auth/userinfo.email"]
        }

    mock_flow_instance.fetch_token = mock_fetch_token

    # Mock userinfo service
    mock_userinfo = MagicMock()
    mock_userinfo_instance = mock_userinfo.return_value
    mock_userinfo_instance.get.return_value.execute.return_value = {
        "sub": "test_user_id",
        "email": "test@example.com",
        "name": "Test User",
        "picture": "https://example.com/picture.jpg"
    }

    # Mock build function
    def mock_build(*args, **kwargs):
        if args[0] == "oauth2":
            return MagicMock(userinfo=mock_userinfo)
        return MagicMock()

    # Mock Flow.from_client_config
    def mock_from_client_config(client_config, *args, **kwargs):
        return mock_flow_instance

    mock_flow.from_client_config = mock_from_client_config

    # Apply patches
    monkeypatch.setattr("src.custom_routes.google.auth.Flow", mock_flow)
    monkeypatch.setattr("src.custom_routes.google.auth.build", mock_build)

    return mock_flow_instance

@pytest.mark.asyncio
async def test_callback_success(client, db_session, mock_google_auth):
    """Test successful Google auth callback."""
    # Set up environment variables
    os.environ["GOOGLE_CLIENT_ID"] = "test_client_id"
    os.environ["GOOGLE_CLIENT_SECRET"] = "test_client_secret"
    os.environ["GOOGLE_REDIRECT_URI"] = "http://localhost:8000/auth/google/store"
    os.environ["GOOGLE_AUTH_STATE"] = "test_state"
    os.environ["GOOGLE_TOKEN_URI"] = "https://oauth2.googleapis.com/token"
    os.environ["GOOGLE_AUTH_URI"] = "https://accounts.google.com/o/oauth2/auth"

    try:
        # First get the auth URL to set up the state
        url_response = client.get("/auth/google/url")
        if url_response.status_code != 200:
            print("Error response:", url_response.json())
        assert url_response.status_code == 200
        state = url_response.json()["state"]

        # Set up session state
        session_data = {"state": state}
        client.cookies.set("session", URLSafeSerializer("test_secret_key").dumps(session_data))

        # Make callback request with valid state
        response = client.get(f"/auth/google/callback?code=test_code&state={state}", follow_redirects=False)
        if response.status_code != 303:
            print("Callback error response:", response.json())
        assert response.status_code == 303  # Redirect status code
        assert response.headers["location"] == "/auth/google/store"

        # Verify user and auth were created
        result = await db_session.execute(select(Users).where(Users.email == "test@example.com"))
        user = result.scalar_one()
        assert user is not None
        assert user.email == "test@example.com"
        assert user.name == "Test User"
        assert user.profile_picture == "https://example.com/picture.jpg"

        result = await db_session.execute(select(GoogleAuth).where(GoogleAuth.user_id == user.id))
        auth = result.scalar_one()
        assert auth is not None
        assert auth.access_token == "test_token"
        assert auth.refresh_token == "test_refresh_token"
    finally:
        # Clean up environment variables
        os.environ.pop("GOOGLE_CLIENT_ID", None)
        os.environ.pop("GOOGLE_CLIENT_SECRET", None)
        os.environ.pop("GOOGLE_REDIRECT_URI", None)
        os.environ.pop("GOOGLE_AUTH_STATE", None)
        os.environ.pop("GOOGLE_TOKEN_URI", None)
        os.environ.pop("GOOGLE_AUTH_URI", None)

@pytest.mark.asyncio
async def test_callback_invalid_state(client):
    """Test callback with invalid state."""
    response = client.get("/auth/google/callback?code=test_code&state=invalid_state")
    assert response.status_code == 400
    assert "Invalid state" in response.json()["detail"]

@pytest.mark.asyncio
async def test_status_connected(client, test_user, db_session):
    """Test checking connection status when connected."""
    # Create a Google auth record
    auth = GoogleAuth(
        user_id=test_user.id,
        email=test_user.email,
        access_token="test_token",
        refresh_token="test_refresh_token",
        token_expiry=datetime.now() + timedelta(hours=1)
    )
    db_session.add(auth)
    await db_session.commit()

    # Set up session cookie
    session_data = {
        "user": {
            "id": str(test_user.id),
            "email": test_user.email,
            "name": test_user.name
        }
    }
    client.cookies.set("session", URLSafeSerializer("test_secret_key").dumps(session_data))

    response = client.get("/auth/google/status")
    assert response.status_code == 200
    data = response.json()
    assert data["connected"] is True
    assert data["user"]["email"] == test_user.email

@pytest.mark.asyncio
async def test_disconnect(client, test_user, db_session):
    """Test disconnecting Google account."""
    # Create a Google auth record
    auth = GoogleAuth(
        user_id=test_user.id,
        email=test_user.email,
        access_token="test_token",
        refresh_token="test_refresh_token",
        token_expiry=datetime.now() + timedelta(hours=1)
    )
    db_session.add(auth)
    await db_session.commit()

    # Create a signed session cookie
    serializer = URLSafeSerializer("test_secret_key")
    session_data = {
        "user": {
            "id": str(test_user.id),
            "email": test_user.email,
            "name": test_user.name
        }
    }
    session_cookie = serializer.dumps(session_data)
    client.cookies.set("session", session_cookie)

    response = client.post("/auth/google/disconnect")
    assert response.status_code == 200

    # Verify auth record was deleted
    result = await db_session.execute(
        select(GoogleAuth).where(GoogleAuth.user_id == test_user.id)
    )
    auth = result.scalar_one_or_none()
    assert auth is None
