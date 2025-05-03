"""
Integration tests for N8N workflow validation.

These tests verify that:
1. Workflows can be created, activated, and deleted
2. Error handling works correctly
3. API responses are handled properly
4. Network conditions are properly handled
"""

import pytest
import pytest_asyncio
import json
from unittest.mock import patch, AsyncMock
import httpx
from fastapi import HTTPException
from src.services.n8n_service import N8nService
from tests.fixtures.n8n_service import MockResponse, MockAsyncClient

@pytest.fixture
def valid_workflow_json():
    """Test workflow JSON data."""
    return {
        "name": "Test Workflow",
        "nodes": [
            {
                "id": "1",
                "name": "Send Email",
                "parameters": {
                    "to": "test@example.com",
                    "subject": "Test Subject",
                    "text": "Test Content"
                },
                "type": "n8n-nodes-base.emailSend"
            }
        ],
        "connections": {},
        "active": False
    }

@pytest.mark.asyncio
async def test_workflow_creation_success(n8n_service, valid_workflow_json):
    """Test successful workflow creation."""
    # Create mock responses
    responses = {
        "http://localhost:5678/healthz": MockResponse(
            status_code=200,
            data={"status": "ok", "version": "1.0.0"}
        ),
        "http://localhost:5678/workflows": MockResponse(
            status_code=200,
            data={"data": {"id": 123}}
        )
    }
    
    # Create mock client
    mock_client = MockAsyncClient(responses)
    
    # Test workflow creation
    with patch("httpx.AsyncClient", return_value=mock_client):
        workflow_result = await n8n_service.create_workflow(valid_workflow_json)
        assert workflow_result["data"]["id"] == 123

@pytest.mark.asyncio
async def test_workflow_creation_missing_name(n8n_service):
    """Test workflow creation with missing name."""
    invalid_workflow = {
        "nodes": [],
        "connections": {}
    }
    
    # Create mock client with default responses
    mock_client = MockAsyncClient()
    
    # Test workflow creation
    with patch("httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(HTTPException) as exc_info:
            await n8n_service.create_workflow(invalid_workflow)
        assert exc_info.value.status_code == 400
        assert "name is required" in str(exc_info.value.detail)

@pytest.mark.asyncio
async def test_workflow_creation_missing_nodes(n8n_service):
    """Test workflow creation with missing nodes."""
    invalid_workflow = {
        "name": "Test Workflow",
        "connections": {}
    }
    
    # Create mock client with default responses
    mock_client = MockAsyncClient()
    
    # Test workflow creation
    with patch("httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(HTTPException) as exc_info:
            await n8n_service.create_workflow(invalid_workflow)
        assert exc_info.value.status_code == 400
        assert "must contain at least one node" in str(exc_info.value.detail)

@pytest.mark.asyncio
async def test_workflow_creation_network_error(n8n_service, valid_workflow_json):
    """Test workflow creation with network error."""
    # Create mock responses with timeout error
    responses = {
        "http://localhost:5678/workflows": MockResponse(
            status_code=503,
            data={"message": "Service unavailable"},
            error=httpx.TimeoutError("Connection timeout")
        )
    }
    
    # Create mock client
    mock_client = MockAsyncClient(responses)
    
    # Test workflow creation
    with patch("httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(httpx.TimeoutError):
            await n8n_service.create_workflow(valid_workflow_json)

@pytest.mark.asyncio
async def test_workflow_creation_server_error(n8n_service, valid_workflow_json):
    """Test workflow creation with server error."""
    # Create mock responses with 500 error
    responses = {
        "http://localhost:5678/workflows": MockResponse(
            status_code=500,
            data={"message": "Internal server error"}
        )
    }
    
    # Create mock client
    mock_client = MockAsyncClient(responses)
    
    # Test workflow creation
    with patch("httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(HTTPException) as exc_info:
            await n8n_service.create_workflow(valid_workflow_json)
        assert exc_info.value.status_code == 500
        assert "Internal server error" in str(exc_info.value.detail)

@pytest.mark.asyncio
async def test_workflow_lifecycle_with_retries(n8n_service, valid_workflow_json):
    """Test complete workflow lifecycle with retries."""
    workflow_id = 123
    
    # Create mock responses with initial failure then success
    responses = {
        "http://localhost:5678/workflows": MockResponse(
            status_code=200,
            data={"data": {"id": workflow_id}}
        ),
        f"http://localhost:5678/workflows/{workflow_id}/activate": [
            MockResponse(
                status_code=503,
                data={"message": "Service temporarily unavailable"},
                error=httpx.TimeoutError("Connection timeout")
            ),
            MockResponse(
                status_code=200,
                data={"data": {"id": workflow_id, "active": True}}
            )
        ],
        f"http://localhost:5678/workflows/{workflow_id}/deactivate": MockResponse(
            status_code=200,
            data={"data": {"id": workflow_id, "active": False}}
        ),
        f"http://localhost:5678/workflows/{workflow_id}": MockResponse(
            status_code=200,
            data={"data": {
                "id": workflow_id,
                "name": valid_workflow_json["name"],
                "active": False
            }}
        )
    }
    
    # Create mock client
    mock_client = MockAsyncClient(responses)
    
    # Test workflow lifecycle
    with patch("httpx.AsyncClient", return_value=mock_client):
        # Create workflow
        created_result = await n8n_service.create_workflow(valid_workflow_json)
        assert created_result["data"]["id"] == workflow_id
        
        # Activate workflow (should retry on timeout)
        await n8n_service.activate_workflow(workflow_id)
        
        # Deactivate workflow
        await n8n_service.deactivate_workflow(workflow_id)
        
        # Delete workflow
        await n8n_service.delete_workflow(workflow_id)

@pytest.mark.asyncio
async def test_workflow_validation_with_invalid_json(n8n_service):
    """Test workflow validation with invalid JSON."""
    invalid_json = "not a json object"
    
    with pytest.raises(HTTPException) as exc_info:
        await n8n_service.create_workflow(invalid_json)
    assert exc_info.value.status_code == 400
    assert "Invalid workflow format" in str(exc_info.value.detail) 