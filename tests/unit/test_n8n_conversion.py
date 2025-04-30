import os
import pytest
from unittest.mock import patch, MagicMock
from src.services.n8n_conversion import N8nConversionService

@pytest.fixture
def n8n_service():
    # Provide a dummy db session (None is fine for these tests)
    return N8nConversionService(db=None)

@pytest.fixture
def workflow_json():
    # Minimal valid workflow JSON for n8n
    return {
        "name": "Test Workflow",
        "nodes": [
            {"id": "1", "type": "test", "name": "Test Node", "parameters": {}}
        ],
        "connections": {},
        "active": False,
        "settings": {},
        "staticData": None
    }

@patch.dict(os.environ, {"N8N_WEBHOOK_URL": "https://example.com", "N8N_API_KEY": "testkey"})
@patch("src.services.n8n_conversion.requests.post")
def test_create_workflow_in_n8n_success(mock_post, n8n_service, workflow_json):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"id": 123, "name": "Test Workflow"}
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    result = n8n_service.create_workflow_in_n8n(workflow_json)
    assert result["id"] == 123
    assert result["name"] == "Test Workflow"
    mock_post.assert_called_once()

@patch.dict(os.environ, {"N8N_WEBHOOK_URL": "https://example.com", "N8N_API_KEY": "testkey"})
@patch("src.services.n8n_conversion.requests.post")
def test_create_workflow_in_n8n_failure(mock_post, n8n_service, workflow_json):
    mock_post.side_effect = Exception("API error")
    with pytest.raises(Exception):
        n8n_service.create_workflow_in_n8n(workflow_json)

@patch.dict(os.environ, {"N8N_WEBHOOK_URL": "https://example.com", "N8N_API_KEY": "testkey"})
@patch("src.services.n8n_conversion.requests.post")
def test_activate_workflow_in_n8n_success(mock_post, n8n_service):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response
    assert n8n_service.activate_workflow_in_n8n(123) is True
    mock_post.assert_called_once()

@patch.dict(os.environ, {"N8N_WEBHOOK_URL": "https://example.com", "N8N_API_KEY": "testkey"})
@patch("src.services.n8n_conversion.requests.post")
def test_activate_workflow_in_n8n_failure(mock_post, n8n_service):
    mock_post.side_effect = Exception("API error")
    with pytest.raises(Exception):
        n8n_service.activate_workflow_in_n8n(123)

@patch.dict(os.environ, {"N8N_WEBHOOK_URL": "https://example.com", "N8N_API_KEY": "testkey"})
@patch("src.services.n8n_conversion.requests.post")
def test_deactivate_workflow_in_n8n_success(mock_post, n8n_service):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response
    assert n8n_service.deactivate_workflow_in_n8n(123) is True
    mock_post.assert_called_once()

@patch.dict(os.environ, {"N8N_WEBHOOK_URL": "https://example.com", "N8N_API_KEY": "testkey"})
@patch("src.services.n8n_conversion.requests.post")
def test_deactivate_workflow_in_n8n_failure(mock_post, n8n_service):
    mock_post.side_effect = Exception("API error")
    with pytest.raises(Exception):
        n8n_service.deactivate_workflow_in_n8n(123) 