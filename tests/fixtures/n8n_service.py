"""
N8N service mock for testing.

This module provides a mock N8N service that can be used in tests to simulate
N8N API responses without making actual HTTP requests.
"""

import pytest
from unittest.mock import AsyncMock, patch, Mock
import json
from typing import Dict, Any, Optional, Union, List
import httpx
from src.services.n8n_service import N8nService
from datetime import timedelta

class MockResponse:
    """Mock response object that simulates httpx.Response."""
    def __init__(self, status_code: int, data: Dict[str, Any], error: Exception = None):
        self.status_code = status_code
        self._data = data
        self.error = error
        self.elapsed = timedelta(seconds=0.1)
        
    def json(self) -> Dict[str, Any]:
        """Return response data as JSON."""
        return self._data
        
    def raise_for_status(self):
        """Raise an error if status code is 400 or greater."""
        if self.error:
            raise self.error
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                message=f"HTTP Error {self.status_code}",
                request=Mock(),
                response=Mock(status_code=self.status_code, text=str(self._data))
            )

class MockAsyncClient:
    """Mock HTTP client that simulates N8N API responses."""
    def __init__(self, responses: Dict[str, Union[MockResponse, List[MockResponse]]] = None):
        self.responses = responses or {}
        self.default_response = MockResponse(
            status_code=200,
            data={"status": "ok", "version": "1.0.0"}
        )
        self.request_history = []
        self.response_index = {}  # Track index for sequence responses
        self.is_closed = False
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.aclose()
        
    async def aclose(self):
        """Close the client."""
        self.is_closed = True
    
    def _get_response(self, url: str) -> MockResponse:
        """Get the appropriate response for a URL, handling sequences."""
        if url not in self.responses:
            return self.default_response
        
        response = self.responses[url]
        if isinstance(response, list):
            # Get current index for this URL, defaulting to 0
            current_index = self.response_index.get(url, 0)
            # Update index for next time
            self.response_index[url] = (current_index + 1) % len(response)
            return response[current_index]
        return response
    
    async def get(self, url: str, **kwargs) -> MockResponse:
        """Simulate GET request."""
        self.request_history.append(("GET", url, kwargs))
        return self._get_response(url)
    
    async def post(self, url: str, **kwargs) -> MockResponse:
        """Simulate POST request."""
        self.request_history.append(("POST", url, kwargs))
        return self._get_response(url)
    
    async def patch(self, url: str, **kwargs) -> MockResponse:
        """Simulate PATCH request."""
        self.request_history.append(("PATCH", url, kwargs))
        return self._get_response(url)
    
    async def put(self, url: str, **kwargs) -> MockResponse:
        """Simulate PUT request."""
        self.request_history.append(("PUT", url, kwargs))
        return self._get_response(url)
    
    async def delete(self, url: str, **kwargs) -> MockResponse:
        """Simulate DELETE request."""
        self.request_history.append(("DELETE", url, kwargs))
        return self._get_response(url)

@pytest.fixture
def mock_n8n_service():
    """Create a mock N8N service for testing.
    
    This fixture:
    1. Creates a mock N8N service instance with test configuration
    2. Patches the httpx.AsyncClient to use our mock client
    3. Returns the service instance
    """
    # Create mock responses
    responses = {
        "http://localhost:5678/healthz": MockResponse(
            status_code=200,
            data={"status": "ok", "version": "1.0.0"}
        ),
        "http://localhost:5678/workflows": MockResponse(
            status_code=200,
            data={"data": {"id": 123}}  # Match actual N8N API response format
        ),
        "http://localhost:5678/workflows/123": MockResponse(
            status_code=200,
            data={"data": {
                "id": 123,
                "name": "Test Workflow",
                "active": False
            }}
        ),
        "http://localhost:5678/workflows/123/activate": MockResponse(
            status_code=200,
            data={"data": {"id": 123, "active": True}}
        ),
        "http://localhost:5678/workflows/123/deactivate": MockResponse(
            status_code=200,
            data={"data": {"id": 123, "active": False}}
        ),
        # Add error cases
        "http://localhost:5678/workflows/404": MockResponse(
            status_code=404,
            data={"message": "Workflow not found"}
        ),
        "http://localhost:5678/workflows/500": MockResponse(
            status_code=500,
            data={"message": "Internal server error"}
        ),
        "http://localhost:5678/workflows/timeout": MockResponse(
            status_code=503,
            data={"message": "Service unavailable"},
            error=httpx.TimeoutError("Connection timeout")
        )
    }
    
    # Create mock client
    mock_client = MockAsyncClient(responses)
    
    # Create service instance with test configuration
    service = N8nService(
        api_url="http://localhost:5678",
        api_key="test_api_key"
    )
    
    # Patch httpx.AsyncClient
    with patch("httpx.AsyncClient", return_value=mock_client):
        yield service