import pytest
import logging
from fastapi.testclient import TestClient
from src.main import app
from src.routes.mantra import get_test_session

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_mantra_creation_with_missing_fields(client, test_user):
    """Test mantra creation with missing required fields"""
    # Create query parameters with missing fields
    params = {
        "name": "Test Mantra",
        # Missing description
        "user_id": test_user.id
    }

    # Create workflow JSON for body
    workflow_json = {
        "nodes": [],
        "connections": {},
        "trigger": {
            "type": "webhook",
            "parameters": {}
        }
    }

    # Log the request details
    logger.debug(f"Sending request with params: {params}")
    logger.debug(f"Request body: {workflow_json}")

    response = client.post("/api/mantras/", params=params, json=workflow_json)
    logger.debug(f"Response status code: {response.status_code}")
    logger.debug(f"Response body: {response.json()}")

    assert response.status_code == 422

def test_mantra_creation_with_valid_data(client, test_user):
    """Test mantra creation with all required fields"""
    # Create request data
    data = {
        "name": "Test Mantra",
        "description": "Test Description",
        "user_id": test_user.id,
        "workflow_json": {
            "nodes": [
                {
                    "id": "1",
                    "type": "gmail",
                    "name": "Send Email",
                    "parameters": {
                        "operation": "sendEmail",
                        "to": "${trigger.email}",
                        "subject": "Test Subject",
                        "text": "Test Body"
                    }
                }
            ],
            "connections": {},
            "trigger": {
                "type": "webhook",
                "parameters": {
                    "email": {"type": "string"}
                }
            }
        }
    }

    # Log the request details
    logger.debug(f"Sending request with data: {data}")

    response = client.post("/api/mantras/", json=data)
    logger.debug(f"Response status code: {response.status_code}")
    logger.debug(f"Response body: {response.json()}")

    assert response.status_code == 200
    assert "id" in response.json()
    assert response.json()["name"] == data["name"] 