"""
N8N service mock for testing.

This module provides a mock N8N service that can be used in tests to simulate
N8N API responses without making actual HTTP requests.
"""

import pytest
from unittest.mock import AsyncMock, patch
import json
from typing import Dict, Any, Optional
import httpx
from src.services.n8n_service import N8nService

class MockResponse:
    """Mock HTTP response."""
    def __init__(self, status_code: int, data: Dict[str, Any], headers: Dict[str, str] = None, error: Optional[Exception] = None):
        self.status_code = status_code
        self._data = data
        self.headers = headers or {"content-type": "application/json"}
        self.text = json.dumps(data)
        self.elapsed = AsyncMock()
        self.elapsed.total_seconds.return_value = 0.1
        self._error = error
    
    async def json(self):
        """Return response data as JSON."""
        if self._error:
            raise self._error
        return self._data
    
    def raise_for_status(self):
        """Raise an exception if status code indicates an error."""
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                message=f"HTTP Error {self.status_code}: {self._data.get('message', 'Unknown error')}",
                request=None,
                response=self
            )
        if self._error:
            raise self._error

class MockAsyncClient:
    """Mock HTTP client that simulates N8N API responses."""
    def __init__(self, responses: Dict[str, MockResponse] = None):
        self.responses = responses or {}
        self.default_response = MockResponse(
            status_code=200,
            data={"status": "ok", "version": "1.0.0"}
        )
        self.request_history = []
    
    async def get(self, url: str, **kwargs) -> MockResponse:
        """Handle GET requests."""
        self.request_history.append(("GET", url, kwargs))
        if url not in self.responses:
            return MockResponse(
                status_code=404,
                data={"message": f"Not found: {url}"}
            )
        return self.responses[url]
    
    async def post(self, url: str, **kwargs) -> MockResponse:
        """Handle POST requests."""
        self.request_history.append(("POST", url, kwargs))
        if url not in self.responses:
            return MockResponse(
                status_code=404,
                data={"message": f"Not found: {url}"}
            )
        
        # Special handling for workflow creation
        if url.endswith("/workflows"):
            json_data = kwargs.get("json", {})
            if not json_data.get("name"):
                return MockResponse(
                    status_code=400,
                    data={"message": "Workflow name is required"}
                )
            if not json_data.get("nodes"):
                return MockResponse(
                    status_code=400,
                    data={"message": "Workflow must contain at least one node"}
                )
        
        return self.responses[url]
    
    async def delete(self, url: str, **kwargs) -> MockResponse:
        """Handle DELETE requests."""
        self.request_history.append(("DELETE", url, kwargs))
        if url not in self.responses:
            return MockResponse(
                status_code=404,
                data={"message": f"Not found: {url}"}
            )
        return self.responses[url]
    
    async def put(self, url: str, **kwargs) -> MockResponse:
        """Handle PUT requests."""
        self.request_history.append(("PUT", url, kwargs))
        if url not in self.responses:
            return MockResponse(
                status_code=404,
                data={"message": f"Not found: {url}"}
            )
        return self.responses[url]
    
    async def __aenter__(self):
        """Enter async context."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context."""
        pass

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