import pytest
from unittest.mock import Mock
from src.services.n8n_service import N8nService

class MockResponse:
    def __init__(self, status_code, data):
        self.status_code = status_code
        self._data = data
        
    def json(self):
        return self._data
        
    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")

class MockAsyncClient:
    def __init__(self, responses):
        self.responses = responses
        
    async def get(self, url, headers=None):
        if url in self.responses:
            return self.responses[url]
        raise Exception(f"No mock response for {url}")
        
    async def post(self, url, headers=None, json=None):
        if url in self.responses:
            return self.responses[url]
        raise Exception(f"No mock response for {url}")

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