"""
Integration tests for N8N workflow validation and creation.

These tests verify that:
1. Workflow JSON validation works correctly
2. Required fields are properly checked
3. N8N API integration functions as expected
4. Error cases are handled appropriately
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
def valid_workflow_json():
    """Fixture providing a valid workflow JSON structure."""
    return {
        "name": "Test Workflow",
        "nodes": [
            {
                "id": "1",
                "type": "n8n-nodes-base.emailSend",
                "name": "Send Email",
                "parameters": {
                    "to": "test@example.com",
                    "subject": "Test Subject",
                    "text": "Test Content"
                }
            }
        ],
        "connections": {},
        "settings": {},
        "active": False,
        "staticData": None
    }

@pytest.fixture
def n8n_service():
    """Create N8nService instance with test configuration."""
    return N8nService(
        api_url="https://test.n8n.cloud/api/v1",
        api_key="test_api_key"
    )

@pytest.mark.asyncio
async def test_workflow_validation_success(n8n_service, valid_workflow_json):
    """Test successful workflow validation."""
    try:
        validated = n8n_service.parse_workflow(valid_workflow_json)
        assert validated["name"] == "Test Workflow"
        assert len(validated["nodes"]) == 1
        assert validated["nodes"][0]["id"] == "1"
        assert validated["nodes"][0]["type"] == "n8n-nodes-base.emailSend"
        assert "connections" in validated
        assert "settings" in validated
        assert "active" in validated
        assert "staticData" in validated
    except ValueError as e:
        pytest.fail(f"Validation should not fail: {str(e)}")

@pytest.mark.asyncio
async def test_workflow_validation_missing_required_fields(n8n_service):
    """Test workflow validation with missing required fields."""
    invalid_workflow = {
        "name": "Invalid Workflow",
        # Missing nodes
        "connections": {}
    }
    
    with pytest.raises(ValueError) as exc_info:
        n8n_service.parse_workflow(invalid_workflow)
    assert "missing required fields" in str(exc_info.value)
    assert "nodes" in str(exc_info.value)

@pytest.mark.asyncio
async def test_workflow_validation_invalid_node_structure(n8n_service):
    """Test workflow validation with invalid node structure."""
    invalid_workflow = {
        "name": "Invalid Node Structure",
        "nodes": [
            {
                "id": "1",
                # Missing type and name
                "parameters": {}
            }
        ],
        "connections": {}
    }
    
    with pytest.raises(ValueError) as exc_info:
        n8n_service.parse_workflow(invalid_workflow)
    assert "missing required fields" in str(exc_info.value)
    assert "type" in str(exc_info.value)
    assert "name" in str(exc_info.value)

@pytest.mark.asyncio
async def test_workflow_creation_success(n8n_service, valid_workflow_json):
    """Test successful workflow creation with mocked N8N API."""
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "application/json"}
    
    async def mock_json():
        return {"id": 123}
    mock_response.json = mock_json
    
    async def mock_post(*args, **kwargs):
        return mock_response

    with patch("httpx.AsyncClient.post", side_effect=mock_post):
        workflow_result = await n8n_service.create_workflow(valid_workflow_json)
        assert workflow_result["id"] == 123

@pytest.mark.asyncio
async def test_workflow_creation_api_error(n8n_service, valid_workflow_json):
    """Test workflow creation with N8N API error response."""
    error_response = {
        "message": "Invalid workflow format",
        "error": "Validation failed"
    }
    
    mock_response = AsyncMock()
    mock_response.status_code = 400
    mock_response.headers = {"content-type": "application/json"}
    mock_response.text = json.dumps(error_response)
    
    async def mock_json():
        return error_response
    mock_response.json = mock_json
    
    async def mock_post(*args, **kwargs):
        raise httpx.HTTPStatusError(
            message="HTTP Error",
            request=None,
            response=mock_response
        )

    with patch("httpx.AsyncClient.post", side_effect=mock_post):
        with pytest.raises(HTTPException) as exc_info:
            await n8n_service.create_workflow(valid_workflow_json)
        
        assert exc_info.value.status_code == 400
        assert "Invalid workflow format" in str(exc_info.value.detail)

@pytest.mark.asyncio
async def test_workflow_creation_network_error(n8n_service, valid_workflow_json):
    """Test workflow creation with network error."""
    with patch("httpx.AsyncClient.post", side_effect=Exception("Network error")):
        with pytest.raises(HTTPException) as exc_info:
            await n8n_service.create_workflow(valid_workflow_json)
        
        assert exc_info.value.status_code == 500
        assert "Failed to create n8n workflow" in str(exc_info.value.detail)

@pytest.mark.asyncio
async def test_workflow_creation_invalid_response(n8n_service, valid_workflow_json):
    """Test workflow creation with invalid API response."""
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "application/json"}
    
    async def mock_json():
        return {"not_id": 123}
    mock_response.json = mock_json
    
    async def mock_post(*args, **kwargs):
        return mock_response

    with patch("httpx.AsyncClient.post", side_effect=mock_post):
        with pytest.raises(HTTPException) as exc_info:
            await n8n_service.create_workflow(valid_workflow_json)
        
        assert exc_info.value.status_code == 400
        assert "missing workflow ID" in str(exc_info.value.detail)

@pytest.mark.asyncio
async def test_end_to_end_workflow_lifecycle(n8n_service, valid_workflow_json):
    """Test complete workflow lifecycle with mocked N8N API."""
    workflow_id = 123
    
    # Create workflow response
    create_response = AsyncMock()
    create_response.status_code = 200
    create_response.headers = {"content-type": "application/json"}
    
    async def create_json():
        return {"id": workflow_id}
    create_response.json = create_json
    
    # Action response (activate/deactivate)
    action_response = AsyncMock()
    action_response.status_code = 200
    action_response.headers = {"content-type": "application/json"}
    
    async def action_json():
        return {}
    action_response.json = action_json
    
    # Delete response
    delete_response = AsyncMock()
    delete_response.status_code = 200
    delete_response.headers = {"content-type": "application/json"}
    
    async def delete_json():
        return {}
    delete_response.json = delete_json
    
    # Create workflow
    async def mock_create_post(*args, **kwargs):
        return create_response
    
    async def mock_action_post(*args, **kwargs):
        return action_response
    
    async def mock_delete(*args, **kwargs):
        return delete_response

    # Test workflow lifecycle
    with patch("httpx.AsyncClient.post", side_effect=mock_create_post):
        created_result = await n8n_service.create_workflow(valid_workflow_json)
        assert created_result["id"] == workflow_id

    with patch("httpx.AsyncClient.post", side_effect=mock_action_post):
        await n8n_service.activate_workflow(workflow_id)

    with patch("httpx.AsyncClient.post", side_effect=mock_action_post):
        await n8n_service.deactivate_workflow(workflow_id)

    with patch("httpx.AsyncClient.delete", side_effect=mock_delete):
        await n8n_service.delete_workflow(workflow_id) 