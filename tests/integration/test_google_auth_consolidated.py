"""
Integration tests for Google auth consolidated endpoints.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
import logging
from unittest.mock import patch, MagicMock
import uuid
from datetime import datetime
from starlette.middleware.sessions import SessionMiddleware
import json
import base64
import itsdangerous

from src.routes.google_auth_consolidated import router as google_auth_router
from src.models.google_integration import GoogleIntegration
from src.models.users import Users
from src.utils.database import get_db

# Disable logging for tests
logging.getLogger("src.routes.google_auth_consolidated").setLevel(logging.ERROR)

# Test secret key
SECRET_KEY = "test_secret"

def create_session_cookie(data: dict) -> str:
    """Create a signed session cookie."""
    signer = itsdangerous.URLSafeSerializer(SECRET_KEY)
    return signer.dumps(data)

@pytest.fixture
def app(db_session):
    """Create test FastAPI app with dependencies."""
    app = FastAPI()
    app.include_router(google_auth_router)
    
    # Add session middleware with same settings as production
    app.add_middleware(
        SessionMiddleware,
        secret_key=SECRET_KEY,
        session_cookie="session",
        same_site="lax",
        https_only=False
    )
    
    # Override get_db dependency
    async def get_test_db():
        yield db_session
    
    app.dependency_overrides[get_db] = get_test_db
    return app

@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)

def test_get_auth_url_saves_state(client):
    """Test that get_auth_url generates and saves state in session."""
    with patch('uuid.uuid4', return_value=uuid.UUID('12345678-1234-5678-1234-567812345678')):
        response = client.get("/api/google/auth")
        assert response.status_code == 200
        data = response.json()
        
        # Verify state was saved in session
        session_cookie = client.cookies["session"]
        serializer = itsdangerous.URLSafeSerializer(SECRET_KEY)
        session = serializer.loads(session_cookie)
        
        assert session["oauth_state"] == "12345678-1234-5678-1234-567812345678"
        assert "auth_url" in data
        assert "state=12345678-1234-5678-1234-567812345678" in data["auth_url"]

def test_callback_verifies_state(client, db_session):
    """Test that callback verifies state from session."""
    # Set up session with state
    state = str(uuid.uuid4())
    session_data = {"oauth_state": state}
    client.cookies["session"] = create_session_cookie(session_data)
    
    # Test with invalid state
    response = client.get(f"/api/google/callback?code=test_code&state=invalid_state")
    assert response.status_code == 307  # Redirect
    assert "error=Invalid state parameter" in response.headers["location"]
    
    # Test with valid state
    response = client.get(f"/api/google/callback?code=test_code&state={state}")
    assert response.status_code == 307  # Redirect
    
    # Verify state was cleared
    session_cookie = client.cookies["session"]
    serializer = itsdangerous.URLSafeSerializer(SECRET_KEY)
    session = serializer.loads(session_cookie)
    assert "oauth_state" not in session

def test_callback_missing_state(client, db_session):
    """Test callback behavior when no state in session."""
    response = client.get("/api/google/callback?code=test_code&state=any_state")
    assert response.status_code == 307  # Redirect
    assert "error=No OAuth state found in session" in response.headers["location"]

def test_callback_clears_state(client, db_session):
    """Test that callback clears state from session after verification."""
    # Set up session with state
    state = str(uuid.uuid4())
    session_data = {"oauth_state": state}
    client.cookies["session"] = create_session_cookie(session_data)
    
    # Mock token and user info responses
    with patch('src.routes.google_auth_consolidated.get_google_token') as mock_token:
        with patch('src.routes.google_auth_consolidated.get_google_user_info') as mock_user_info:
            mock_token.return_value = {
                "access_token": "test_token",
                "refresh_token": "test_refresh",
                "expires_in": 3600,
                "scope": "email profile"
            }
            mock_user_info.return_value = {
                "sub": "test_id",
                "email": "test@example.com",
                "name": "Test User"
            }
            
            response = client.get(f"/api/google/callback?code=test_code&state={state}")
            assert response.status_code == 307  # Redirect
            
            # Verify state was cleared
            session_cookie = client.cookies["session"]
            serializer = itsdangerous.URLSafeSerializer(SECRET_KEY)
            session = serializer.loads(session_cookie)
            assert "oauth_state" not in session 