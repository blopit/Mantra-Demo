"""
Integration tests for application startup behavior.
"""

import pytest
from fastapi.testclient import TestClient
import logging
from unittest.mock import AsyncMock, patch, MagicMock
import os

from app import app
from src.utils.database import init_db

# Disable logging for tests
logging.getLogger("app").setLevel(logging.ERROR)

@pytest.mark.asyncio
async def test_app_startup():
    """Test that the application startup correctly initializes the database."""
    # Mock init_db to track if it was called
    mock_init_db = AsyncMock()
    
    with patch("app.init_db", mock_init_db):
        with TestClient(app) as client:
            # The TestClient will trigger startup events
            response = client.get("/")
            
            # Verify that init_db was called
            mock_init_db.assert_called_once()

@pytest.mark.asyncio
async def test_app_startup_database_error():
    """Test that the application handles database initialization errors."""
    # Mock init_db to raise an exception
    mock_init_db = AsyncMock(side_effect=Exception("Database error"))
    
    with patch("app.init_db", mock_init_db):
        with pytest.raises(Exception) as exc_info:
            with TestClient(app):
                pass  # The error should be raised during startup
        
        assert str(exc_info.value) == "Database error"
        mock_init_db.assert_called_once() 