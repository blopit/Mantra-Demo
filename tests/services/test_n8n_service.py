import pytest
import pytest_asyncio
import json
from unittest.mock import patch, AsyncMock
import httpx
from fastapi import HTTPException
from src.services.n8n_service import N8nService
from tests.fixtures.n8n_service import MockResponse, MockAsyncClient

@pytest.mark.asyncio
async def test_webhook_url_generation():
    """Test webhook URL generation with different parameter configurations."""
    test_cases = [
        # Standard path parameter
        {
            "workflow": {
                "nodes": [{
                    "type": "n8n-nodes-base.webhook",
                    "parameters": {"path": "test-webhook"}
                }]
            },
            "expected_path": "test-webhook"
        },
        # Endpoint parameter
        {
            "workflow": {
                "nodes": [{
                    "type": "n8n-nodes-base.webhook",
                    "parameters": {"endpoint": "custom-endpoint"}
                }]
            },
            "expected_path": "custom-endpoint"
        },
        # Nested in options
        {
            "workflow": {
                "nodes": [{
                    "type": "n8n-nodes-base.webhook",
                    "parameters": {"options": {"path": "nested-path"}}
                }]
            },
            "expected_path": "nested-path"
        },
        # Default fallback
        {
            "workflow": {
                "nodes": [{
                    "type": "n8n-nodes-base.webhook",
                    "parameters": {}
                }]
            },
            "expected_path": "webhook"
        }
    ]
    
    for i, test_case in enumerate(test_cases):
        # Setup mock responses
        mock_responses = {
            f"https://n8n.example.com/api/v1/workflows/{i}": MockResponse(
                status_code=200,
                data=test_case["workflow"]
            )
        }
        
        # Create service with mock client
        service = N8nService(
            api_url="https://n8n.example.com/api/v1",
            api_key="test-key"
        )
        service._client = MockAsyncClient(responses=mock_responses)
        
        # Get webhook URL
        webhook_url = await service.get_webhook_url(str(i))
        
        # Verify URL
        expected_url = f"https://n8n.example.com/webhook/{i}/{test_case['expected_path']}"
        assert webhook_url == expected_url, f"Test case {i} failed: expected {expected_url}, got {webhook_url}"

@pytest.mark.asyncio
async def test_webhook_workflow_execution():
    """Test execution of a webhook-triggered workflow."""
    # Mock responses
    mock_responses = {
        "https://n8n.example.com/api/v1/workflows/123": MockResponse(
            status_code=200,
            data={
                "id": "123",
                "active": True,
                "nodes": [
                    {
                        "type": "n8n-nodes-base.webhook",
                        "parameters": {
                            "path": "test-webhook"
                        }
                    }
                ]
            }
        ),
        "https://n8n.example.com/webhook/123/test-webhook": MockResponse(
            status_code=200,
            data={
                "data": {
                    "result": "success"
                },
                "executionId": "abc123"
            }
        )
    }
    
    # Create service with mock client
    service = N8nService(
        api_url="https://n8n.example.com/api/v1",
        api_key="test-key"
    )
    service._client = MockAsyncClient(responses=mock_responses)
    
    # Execute workflow
    result = await service.execute_workflow(
        workflow_id="123",
        data={"test": "data"}
    )
    
    # Verify result
    assert result["success"] is True
    assert result["execution_id"] == "abc123"
    assert result["data"]["result"] == "success"
    
    # Verify webhook URL was used
    webhook_url = await service.get_webhook_url("123")
    assert webhook_url == "https://n8n.example.com/webhook/123/test-webhook"

@pytest.mark.asyncio
async def test_webhook_activation_with_404_retry():
    """Test webhook activation with 404 retry logic.
    
    This test verifies that:
    1. The service attempts to activate a workflow with webhook
    2. Handles initial 404 error from webhook test
    3. Retries activation and webhook registration
    4. Successfully verifies webhook after retry
    """
    # Mock responses for different stages of the test
    mock_responses = {
        # Initial workflow fetch
        "https://n8n.example.com/api/v1/workflows/123": MockResponse(
            status_code=200,
            data={
                "id": "123",
                "nodes": [{
                    "type": "n8n-nodes-base.webhook",
                    "parameters": {"path": "test-webhook"}
                }],
                "active": False
            }
        ),
        # PATCH activation attempt
        "https://n8n.example.com/api/v1/workflows/123": MockResponse(
            status_code=200,
            data={"id": "123", "active": True}
        ),
        # Webhook test endpoint with sequence of responses
        "https://n8n.example.com/webhook/123/test-webhook": [
            # First attempt - 404
            MockResponse(
                status_code=404,
                data={"message": "Not Found"}
            ),
            # Second attempt - success
            MockResponse(
                status_code=200,
                data={"success": True}
            )
        ]
    }
    
    # Create service with mock client
    service = N8nService(
        api_url="https://n8n.example.com/api/v1",
        api_key="test-key"
    )
    
    async with httpx.AsyncClient() as client:
        # Create and use our mock client
        mock_client = MockAsyncClient(mock_responses)
        
        with patch('httpx.AsyncClient', return_value=mock_client):
            # Attempt to activate workflow
            result = await service.activate_workflow("123")
            
            # Verify the result
            assert result is True, "Workflow activation should succeed after retry"
            
            # Get all requests made
            requests = mock_client.request_history
            
            # Verify workflow was fetched first
            assert any(
                req[0] == "GET" and req[1].endswith("/workflows/123")
                for req in requests
            ), "Should fetch workflow first"
            
            # Verify PATCH activation was attempted
            patch_calls = [
                req for req in requests
                if req[0] == "PATCH" and req[1].endswith("/123")
            ]
            assert len(patch_calls) > 0, "Should attempt PATCH activation"
            assert patch_calls[0][2].get("json", {}).get("active") is True, "Should set active=true"
            
            # Verify webhook test sequence
            webhook_calls = [
                req for req in requests 
                if "webhook" in req[1]
            ]
            assert len(webhook_calls) >= 2, "Should test webhook multiple times"
            
            # Verify webhook test retries
            webhook_responses = [
                mock_client._get_response("https://n8n.example.com/webhook/123/test-webhook")
                for _ in range(2)
            ]
            assert webhook_responses[0].status_code == 404, "First webhook test should fail"
            assert webhook_responses[1].status_code == 200, "Second webhook test should succeed"
            
            # Verify proper delays between retries
            assert len([
                req for req in requests
                if isinstance(req[2].get("timeout"), (int, float))
            ]) > 0, "Requests should have timeouts set"

@pytest.mark.asyncio
async def test_create_and_activate_sample_workflow():
    """Test creating and activating a sample workflow with webhook.
    
    This test demonstrates the complete lifecycle of:
    1. Creating a workflow with webhook node
    2. Activating the workflow
    3. Verifying webhook registration
    4. Testing webhook execution
    """
    # Sample workflow definition with webhook
    sample_workflow = {
        "name": "Sample Onboarding Workflow",
        "nodes": [
            {
                "id": "1",
                "type": "n8n-nodes-base.webhook",
                "name": "Webhook Trigger",
                "parameters": {
                    "path": "onboarding",
                    "responseMode": "responseNode",
                    "options": {}
                }
            },
            {
                "id": "2",
                "type": "n8n-nodes-base.gmail",
                "name": "Send Email",
                "parameters": {
                    "operation": "sendEmail",
                    "to": "{{$node[\"Webhook Trigger\"].data.email}}",
                    "subject": "Welcome to Mantra!",
                    "text": "Thanks for trying out our workflow automation!"
                }
            }
        ],
        "connections": {
            "Webhook Trigger": {
                "main": [[{
                    "node": "Send Email",
                    "type": "main",
                    "index": 0
                }]]
            }
        }
    }

    # Mock responses for the complete workflow lifecycle
    mock_responses = {
        # Health check endpoint
        "https://n8n.example.com/healthz": MockResponse(
            status_code=200,
            data={"status": "ok", "version": "1.0.0"}
        ),
        # Create workflow
        "https://n8n.example.com/api/v1/workflows": MockResponse(
            status_code=200,
            data={
                "id": "123",
                "name": sample_workflow["name"],
                "active": False,
                "nodes": sample_workflow["nodes"],
                "connections": sample_workflow["connections"]
            }
        ),
        # Get workflow
        "https://n8n.example.com/api/v1/workflows/123": [
            # Initial state
            MockResponse(
                status_code=200,
                data={
                    "id": "123",
                    "name": sample_workflow["name"],
                    "nodes": sample_workflow["nodes"],
                    "connections": sample_workflow["connections"],
                    "active": False
                }
            ),
            # After activation
            MockResponse(
                status_code=200,
                data={
                    "id": "123",
                    "name": sample_workflow["name"],
                    "nodes": sample_workflow["nodes"],
                    "connections": sample_workflow["connections"],
                    "active": True
                }
            )
        ],
        # Activate workflow (PATCH)
        "https://n8n.example.com/api/v1/workflows/123": MockResponse(
            status_code=200,
            data={
                "id": "123",
                "active": True
            }
        ),
        # Execute workflow
        "https://n8n.example.com/api/v1/workflows/123/execute": MockResponse(
            status_code=200,
            data={
                "data": {
                    "message": "Welcome email sent"
                },
                "executionId": "abc123"
            }
        ),
        # Webhook execution
        "https://n8n.example.com/webhook/123/onboarding": [
            # Initial 404 during registration
            MockResponse(
                status_code=404,
                data={"message": "Not Found"}
            ),
            # Success after registration
            MockResponse(
                status_code=200,
                data={
                    "data": {
                        "message": "Welcome email sent"
                    },
                    "executionId": "abc123"
                }
            )
        ]
    }

    # Create service with mock client
    service = N8nService(
        api_url="https://n8n.example.com/api/v1",
        api_key="test-key"
    )

    # Create and use our mock client
    mock_client = MockAsyncClient(mock_responses)

    # Mock the httpx.AsyncClient to return our mock client
    with patch('httpx.AsyncClient', return_value=mock_client):
        # Step 1: Create the workflow
        created_workflow = await service.create_workflow(sample_workflow)
        assert created_workflow["id"] == "123"
        assert created_workflow["name"] == sample_workflow["name"]
        assert not created_workflow["active"]

        # Step 2: Activate the workflow
        activated = await service.activate_workflow("123")
        assert activated is True

        # Step 3: Execute the workflow
        execution_result = await service.execute_workflow("123", {"email": "test@example.com"})
        assert execution_result["success"] is True
        assert execution_result["execution_id"] == "abc123"
        assert execution_result["data"]["message"] == "Welcome email sent" 