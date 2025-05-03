import pytest
import httpx
import asyncio
from unittest.mock import patch, MagicMock
from fastapi import HTTPException
from src.services.n8n_service import N8nService
from src.services.mantra_service import MantraService

@pytest.fixture
def n8n_service():
    """Create a test N8N service instance."""
    return N8nService(
        api_url="http://localhost:5678",
        api_key="test_api_key"
    )

@pytest.mark.asyncio
async def test_n8n_connection_success(n8n_service):
    """Test successful N8N service connection."""
    with patch('httpx.AsyncClient.get') as mock_get:
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"status": "ok", "version": "1.0.0"}
        )
        
        result = await n8n_service.check_connection()
        
        assert result["is_connected"] is True
        assert result["status"] == "ok"
        assert result["version"] == "1.0.0"
        assert "response_time_ms" in result

@pytest.mark.asyncio
async def test_n8n_connection_retry(n8n_service):
    """Test N8N service connection retry mechanism."""
    with patch('httpx.AsyncClient.get') as mock_get:
        # First two calls fail, third succeeds
        mock_get.side_effect = [
            httpx.ConnectError("Connection refused"),
            httpx.ConnectError("Connection refused"),
            MagicMock(
                status_code=200,
                json=lambda: {"status": "ok", "version": "1.0.0"}
            )
        ]
        
        result = await n8n_service.check_connection()
        
        assert result["is_connected"] is True
        assert mock_get.call_count == 3

@pytest.mark.asyncio
async def test_n8n_connection_failure(n8n_service):
    """Test N8N service connection failure after max retries."""
    with patch('httpx.AsyncClient.get') as mock_get:
        mock_get.side_effect = httpx.ConnectError("Connection refused")
        
        with pytest.raises(HTTPException) as exc_info:
            await n8n_service.check_connection()
        
        assert exc_info.value.status_code == 503
        assert "Failed to connect to n8n service after 3 attempts" in str(exc_info.value.detail)
        assert mock_get.call_count == 3

@pytest.mark.asyncio
async def test_n8n_unauthorized_access(n8n_service):
    """Test N8N service unauthorized access."""
    with patch('httpx.AsyncClient.get') as mock_get:
        # Create a mock response with 401 status code
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_response.json = lambda: {"error": "Unauthorized"}
        mock_response.elapsed = MagicMock()
        mock_response.elapsed.total_seconds = lambda: 0.1
        
        # Raise 401 error directly
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
async def test_mantra_installation_n8n_unavailable(n8n_service):
    """Test mantra installation when N8N service is unavailable."""
    # Mock the database session
    db_session = MagicMock()
    
    # Create MantraService instance with mocked dependencies
    mantra_service = MantraService(
        db_session=db_session,
        n8n_service=n8n_service
    )
    
    # Mock N8N service to always fail
    with patch('httpx.AsyncClient.get') as mock_get:
        mock_get.side_effect = httpx.ConnectError("Connection refused")
        
        with pytest.raises(HTTPException) as exc_info:
            await mantra_service.install_mantra(
                mantra_id="test-mantra-id",
                user_id="test-user-id"
            )
        
        assert exc_info.value.status_code == 503
        assert "n8n service is not available" in str(exc_info.value.detail)

@pytest.mark.asyncio
async def test_n8n_connection_timeout(n8n_service):
    """Test N8N service connection timeout."""
    with patch('httpx.AsyncClient.get') as mock_get:
        mock_get.side_effect = httpx.TimeoutException("Connection timed out")
        
        with pytest.raises(HTTPException) as exc_info:
            await n8n_service.check_connection()
        
        assert exc_info.value.status_code == 503
        assert "Failed to connect to n8n service" in str(exc_info.value.detail)

@pytest.mark.asyncio
async def test_n8n_invalid_response(n8n_service):
    """Test N8N service invalid response handling."""
    with patch('httpx.AsyncClient.get') as mock_get:
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"invalid": "response"}
        )
        
        result = await n8n_service.check_connection()
        
        assert result["is_connected"] is False
        assert "Invalid response from n8n service" in result["error"] 