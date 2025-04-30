"""
Test script for workflow creation and execution.
"""
import json
import pytest
import pytest_asyncio
from datetime import datetime, timedelta
import os
import pathlib
from fastapi.testclient import TestClient
from sqlalchemy import select
from src.models.mantra import Mantra, MantraInstallation

def load_workflow_fixture():
    """Load the test workflow fixture."""
    fixture_path = pathlib.Path(__file__).parent.parent / "fixtures" / "test_workflow.json"
    with open(fixture_path) as f:
        return json.load(f)

@pytest.mark.asyncio
async def test_workflow_creation(client, test_user, db_session, mock_n8n_service):
    """Test creating and executing a workflow."""
    # Load test workflow from fixture
    workflow_data = load_workflow_fixture()
    
    # Mock n8n service responses
    mock_n8n_service.create_workflow.return_value = {"id": 123}
    mock_n8n_service.execute_workflow.return_value = {"success": True}
    
    # Create workflow
    create_response = client.post(
        "/api/mantras/",
        json={
            "name": workflow_data["name"],
            "description": workflow_data["description"],
            "workflow_json": workflow_data["workflow_json"],
            "user_id": test_user.id,
            "is_active": True
        }
    )
    
    assert create_response.status_code == 200
    mantra_id = create_response.json()["id"]
    
    # Verify mantra was created
    result = await db_session.execute(
        select(Mantra).where(Mantra.id == mantra_id)
    )
    mantra = result.scalar_one_or_none()
    assert mantra is not None
    assert mantra.name == workflow_data["name"]
    assert mantra.description == workflow_data["description"]
    assert mantra.workflow_json == workflow_data["workflow_json"]
    assert mantra.user_id == test_user.id
    assert mantra.is_active is True
    
    # Install workflow
    install_response = client.post(
        f"/api/mantras/{mantra_id}/install?user_id={test_user.id}"
    )
    
    assert install_response.status_code == 200
    assert "id" in install_response.json()
    assert "status" in install_response.json()
    assert install_response.json()["status"] == "active"
    
    # Execute workflow with ISO formatted datetime
    preferred_time = (datetime.now() + timedelta(days=1)).replace(hour=10, minute=0).isoformat()
    execute_response = client.post(
        f"/api/mantras/installations/{install_response.json()['id']}/execute",
        json={
            "email": test_user.email,
            "preferredTime": preferred_time
        }
    )
    
    assert execute_response.status_code == 200
    result = execute_response.json()
    assert "result" in result
    assert result["installation_id"] == install_response.json()["id"] 