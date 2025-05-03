"""
Integration tests for N8N service connection.

These tests verify that:
1. N8N service connection can be established
2. Environment variables are properly configured
3. Connection errors are properly handled and logged
4. Health check endpoint works correctly
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock
import json
import os
from datetime import datetime
from fastapi import HTTPException
import httpx

from src.services.n8n_service import N8nService

@pytest.fixture
def mock_env():
    """Set up test environment variables."""
    with patch.dict(os.environ, {
        "N8N_API_URL": "http://localhost:5678/api/v1",
        "N8N_API_KEY": "test-key",
        "N8N_API_TIMEOUT": "5.0",
        "N8N_MAX_RETRIES": "3",
        "N8N_RETRY_DELAY": "0.1"
    }):
        yield

@pytest.fixture
def n8n_service(mock_env):
    """Create N8nService instance with test configuration."""
    return N8nService(
        api_url=os.environ["N8N_API_URL"],
        api_key=os.environ["N8N_API_KEY"]
    )

@pytest.mark.asyncio
async def test_check_connection_success(n8n_service):
    """Test successful connection to n8n service."""
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "ok"}
        mock_get.return_value = mock_response

        health_status = await n8n_service.check_connection()
        assert health_status["status"] == "ok"
        assert health_status["is_connected"] is True

@pytest.mark.asyncio
async def test_check_connection_failure(n8n_service):
    """Test connection failure handling."""
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.side_effect = httpx.ConnectError("Failed to connect")

        with pytest.raises(HTTPException) as exc_info:
            await n8n_service.check_connection()
        
        assert exc_info.value.status_code == 503
        assert "Failed to connect to n8n service" in str(exc_info.value.detail)

@pytest.mark.asyncio
async def test_check_connection_invalid_response(n8n_service):
    """Test handling of invalid response from n8n service."""
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"invalid": "response"}
        mock_get.return_value = mock_response

        health_status = await n8n_service.check_connection()
        assert health_status["is_connected"] is False
        assert "Invalid response" in health_status["error"]

@pytest.mark.asyncio
async def test_check_connection_unauthorized(n8n_service):
    """Test handling of unauthorized access."""
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_get.side_effect = httpx.HTTPStatusError(
            "401 Unauthorized",
            request=MagicMock(),
            response=mock_response
        )

        with pytest.raises(HTTPException) as exc_info:
            await n8n_service.check_connection()
        
        assert exc_info.value.status_code == 401
        assert "Unauthorized access to n8n service" in str(exc_info.value.detail)

@pytest.mark.asyncio
async def test_validate_environment(n8n_service):
    """Test environment validation."""
    # Should pass with mock_env fixture
    n8n_service.validate_environment()

    # Test missing API URL
    n8n_service.api_url = ""
    with pytest.raises(ValueError) as exc_info:
        n8n_service.validate_environment()
    assert "N8N_API_URL is not configured" in str(exc_info.value)

    # Test missing API key
    n8n_service.api_url = "http://localhost:5678/api/v1"
    n8n_service.api_key = ""
    with pytest.raises(ValueError) as exc_info:
        n8n_service.validate_environment()
    assert "N8N_API_KEY is not configured" in str(exc_info.value)

@pytest.mark.asyncio
async def test_connection_retry_backoff(n8n_service):
    """Test connection retry with backoff."""
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.side_effect = [
            httpx.ConnectError("Failed attempt 1"),
            httpx.ConnectError("Failed attempt 2"),
            MagicMock(status_code=200, json=lambda: {"status": "ok"})
        ]

        health_status = await n8n_service.check_connection()
        assert health_status["status"] == "ok"
        assert health_status["is_connected"] is True
        assert mock_get.call_count == 3 