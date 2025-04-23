"""
Test configuration for pytest.
"""

import os
import sys
import json
import pytest
from pathlib import Path

# Add the project root directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import project modules
from src.utils.google_credentials import (
    get_credentials_from_database_url,
    store_credentials_in_database_url,
    clear_credentials_from_database_url
)


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
