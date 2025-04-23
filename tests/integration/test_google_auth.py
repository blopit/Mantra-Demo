"""
Integration tests for Google authentication flow.
"""

import os
import json
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

# Import the router to test
from src.custom_routes.google.auth import router as google_auth_router


# Create a test FastAPI app
app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="test_secret")
app.include_router(google_auth_router)
client = TestClient(app)


class TestGoogleAuthFlow:
    """Tests for Google authentication flow."""

    @patch("src.custom_routes.google.auth.get_auth_manager")
    def test_auth_url_generation(self, mock_get_auth_manager):
        """Test generating Google auth URL."""
        # Mock auth manager
        mock_auth_manager = MagicMock()
        mock_auth_manager.get_authorization_url.return_value = "https://accounts.google.com/o/oauth2/auth?test=1"
        mock_get_auth_manager.return_value = mock_auth_manager

        # Make request
        response = client.get("/api/google/auth")
        
        # Check response
        assert response.status_code == 200
        assert response.json() == {"auth_url": "https://accounts.google.com/o/oauth2/auth?test=1"}
        mock_auth_manager.get_authorization_url.assert_called_once()

    @patch("src.custom_routes.google.auth.get_auth_manager")
    def test_auth_url_error(self, mock_get_auth_manager):
        """Test error handling when generating auth URL."""
        # Mock auth manager to raise exception
        mock_auth_manager = MagicMock()
        mock_auth_manager.get_authorization_url.side_effect = Exception("Test error")
        mock_get_auth_manager.return_value = mock_auth_manager

        # Make request
        response = client.get("/api/google/auth")
        
        # Check response
        assert response.status_code == 500
        assert "Test error" in response.json()["detail"]

    @patch("src.custom_routes.google.auth.get_auth_manager")
    @patch("src.custom_routes.google.auth.get_user_info")
    @patch("src.custom_routes.google.auth.get_or_create_user")
    @patch("src.custom_routes.google.auth.store_credentials")
    @patch("src.custom_routes.google.auth.store_credentials_in_database_url")
    def test_callback_success(
        self, 
        mock_store_in_db_url,
        mock_store_credentials, 
        mock_get_or_create_user, 
        mock_get_user_info, 
        mock_get_auth_manager
    ):
        """Test successful OAuth callback."""
        # Mock auth manager
        mock_auth_manager = MagicMock()
        mock_credentials_manager = MagicMock()
        mock_credentials_manager.exchange_code.return_value = {
            "access_token": "test_token",
            "refresh_token": "test_refresh_token"
        }
        mock_auth_manager.credentials_manager = mock_credentials_manager
        mock_get_auth_manager.return_value = mock_auth_manager
        
        # Mock user info
        mock_get_user_info.return_value = {"email": "test@example.com", "sub": "123456"}
        
        # Mock user creation
        mock_get_or_create_user.return_value = "user_id_123"
        
        # Mock session
        client.cookies.update({"session": "test_session"})
        
        # Make request with session state
        with client.session_transaction() as session:
            session["oauth_state"] = "test_state"
            session["store_in_db_url"] = True
        
        response = client.get("/api/google/callback?code=test_code&state=test_state")
        
        # Check response
        assert response.status_code == 200
        
        # Verify function calls
        mock_credentials_manager.exchange_code.assert_called_once()
        mock_get_user_info.assert_called_once()
        mock_get_or_create_user.assert_called_once()
        mock_store_credentials.assert_called_once()
        mock_store_in_db_url.assert_called_once()

    @patch("src.custom_routes.google.auth.get_auth_manager")
    def test_callback_state_mismatch(self, mock_get_auth_manager):
        """Test OAuth callback with state mismatch."""
        # Mock session
        client.cookies.update({"session": "test_session"})
        
        # Make request with mismatched state
        with client.session_transaction() as session:
            session["oauth_state"] = "correct_state"
        
        response = client.get("/api/google/callback?code=test_code&state=wrong_state")
        
        # Check response
        assert response.status_code == 400
        assert "Invalid state parameter" in response.json()["detail"]

    @patch("src.custom_routes.google.auth.get_auth_manager")
    def test_callback_exchange_error(self, mock_get_auth_manager):
        """Test OAuth callback with token exchange error."""
        # Mock auth manager
        mock_auth_manager = MagicMock()
        mock_credentials_manager = MagicMock()
        mock_credentials_manager.exchange_code.return_value = None  # Simulate exchange failure
        mock_auth_manager.credentials_manager = mock_credentials_manager
        mock_get_auth_manager.return_value = mock_auth_manager
        
        # Mock session
        client.cookies.update({"session": "test_session"})
        
        # Make request with session state
        with client.session_transaction() as session:
            session["oauth_state"] = "test_state"
        
        response = client.get("/api/google/callback?code=test_code&state=test_state")
        
        # Check response
        assert response.status_code == 500
        assert "Failed to exchange code for tokens" in response.json()["detail"]

    def test_store_in_db_url(self):
        """Test setting flag to store credentials in DATABASE_URL."""
        response = client.get("/api/google/store-in-db-url")
        
        # Check response is a redirect
        assert response.status_code == 307
        assert response.headers["location"] == "/api/google/auth"
        
        # Check session flag was set
        with client.session_transaction() as session:
            assert session["store_in_db_url"] is True

    @patch("src.custom_routes.google.auth.get_current_user")
    @patch("src.custom_routes.google.auth.get_db")
    def test_status_connected(self, mock_get_db, mock_get_current_user):
        """Test getting Google connection status when connected."""
        # Mock user
        mock_user = MagicMock()
        mock_user.id = "user_id_123"
        mock_get_current_user.return_value = mock_user
        
        # Mock database session
        mock_db = MagicMock()
        mock_integration = MagicMock()
        mock_integration.email = "test@example.com"
        mock_integration.scopes = ["https://www.googleapis.com/auth/userinfo.email"]
        mock_db.query.return_value.filter.return_value.first.return_value = mock_integration
        mock_get_db.return_value = mock_db
        
        # Make request
        response = client.get("/api/google/status")
        
        # Check response
        assert response.status_code == 200
        assert response.json() == {
            "is_connected": True,
            "email": "test@example.com",
            "scopes": ["https://www.googleapis.com/auth/userinfo.email"]
        }

    @patch("src.custom_routes.google.auth.get_current_user")
    @patch("src.custom_routes.google.auth.get_db")
    def test_status_not_connected(self, mock_get_db, mock_get_current_user):
        """Test getting Google connection status when not connected."""
        # Mock user
        mock_user = MagicMock()
        mock_user.id = "user_id_123"
        mock_get_current_user.return_value = mock_user
        
        # Mock database session with no integration
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_get_db.return_value = mock_db
        
        # Make request
        response = client.get("/api/google/status")
        
        # Check response
        assert response.status_code == 200
        assert response.json() == {
            "is_connected": False,
            "email": None
        }

    @patch("src.custom_routes.google.auth.get_current_user")
    @patch("src.custom_routes.google.auth.get_db")
    @patch("src.custom_routes.google.auth.clear_credentials_from_database_url")
    def test_disconnect(self, mock_clear_credentials, mock_get_db, mock_get_current_user):
        """Test disconnecting Google account."""
        # Mock user
        mock_user = MagicMock()
        mock_user.id = "user_id_123"
        mock_get_current_user.return_value = mock_user
        
        # Mock database session
        mock_db = MagicMock()
        mock_integration = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_integration
        mock_get_db.return_value = mock_db
        
        # Make request
        response = client.get("/api/google/disconnect")
        
        # Check response
        assert response.status_code == 200
        assert response.json() == {
            "success": True,
            "message": "Google account disconnected"
        }
        
        # Verify function calls
        mock_integration.status = "disconnected"
        mock_db.commit.assert_called_once()
        mock_clear_credentials.assert_called_once()
