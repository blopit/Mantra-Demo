"""
End-to-end tests for the mantra workflow endpoints.

These tests verify the complete flow of mantra operations through the API,
including installation, uninstallation, and workflow execution.
"""

import pytest
import pytest_asyncio
from uuid import uuid4
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import json

from src.models.mantra import Mantra, MantraInstallation
from src.services.n8n_service import N8nService

@pytest.fixture
def mock_n8n_service():
    """Mock n8n service for e2e tests."""
    with patch("src.services.n8n_service.N8nService") as mock:
        instance = mock.return_value
        # Mock successful workflow creation
        instance.create_workflow = AsyncMock(return_value={"id": 123})
        # Mock successful workflow activation
        instance.activate_workflow = AsyncMock(return_value={"id": 123, "active": True})
        # Mock successful workflow deactivation
        instance.deactivate_workflow = AsyncMock(return_value={"id": 123, "active": False})
        # Mock successful workflow deletion
        instance.delete_workflow = AsyncMock(return_value=True)
        # Mock successful workflow execution
        instance.execute_workflow = AsyncMock(return_value={
            "success": True,
            "result": {
                "execution_id": "test-execution-id",
                "status": "success",
                "data": {"output": "test output"}
            }
        })
        # Mock successful workflow parsing
        instance.parse_workflow = AsyncMock(return_value={"nodes": [], "connections": {}})
        yield instance

@pytest_asyncio.fixture
async def test_mantra(db_session: AsyncSession, test_user) -> Mantra:
    """Create a test mantra."""
    mantra = Mantra(
        name="Test Mantra",
        description="Test Description",
        workflow_json={
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
            "connections": {}
        },
        user_id=test_user.id,
        is_active=True
    )
    db_session.add(mantra)
    await db_session.commit()
    await db_session.refresh(mantra)
    return mantra

@pytest.mark.asyncio
async def test_install_mantra(client, test_mantra, test_user, db_session):
    """Test installing a mantra."""
    # Set session data using cookies
    session_data = {
        "user": {
            "id": str(test_user.id),  # Convert UUID to string
            "email": test_user.email,
            "name": test_user.name
        }
    }
    client.cookies.set("session", json.dumps(session_data))

    # Make the installation request with user_id as query parameter
    response = client.post(
        f"/api/mantras/{test_mantra.id}/install?user_id={str(test_user.id)}"
    )
    assert response.status_code == 200
    
    # Verify the response
    data = response.json()
    assert "installation_id" in data
    assert data["mantra_id"] == str(test_mantra.id)
    
    # Verify the installation was created in the database
    installation = await db_session.get(MantraInstallation, data["installation_id"])
    assert installation is not None
    assert installation.mantra_id == test_mantra.id
    assert installation.user_id == test_user.id
    assert installation.status == "active"

@pytest.mark.asyncio
async def test_uninstall_mantra(
    client: TestClient,
    test_mantra: Mantra,
    test_user,
    db_session: AsyncSession,
    mock_n8n_service
):
    """Test uninstalling a mantra."""
    # Create an installation first
    installation = MantraInstallation(
        mantra_id=test_mantra.id,
        user_id=test_mantra.user_id,
        n8n_workflow_id=123,
        status="active"
    )
    db_session.add(installation)
    await db_session.commit()
    await db_session.refresh(installation)

    # Set session data using cookies
    session_data = {
        "user": {
            "id": str(test_user.id),  # Convert UUID to string
            "email": test_user.email,
            "name": test_user.name
        }
    }
    client.cookies.set("session", json.dumps(session_data))

    # Mock N8nService response
    mock_n8n_service.delete_workflow.return_value = True

    # Uninstall mantra
    response = client.delete(
        f"/api/mantras/installations/{installation.id}",
    )
    assert response.status_code == 200

    # Verify database state
    result = await db_session.execute(
        select(MantraInstallation).where(MantraInstallation.id == installation.id)
    )
    installation = result.scalar_one_or_none()
    assert installation is None

    # Verify N8n service was called
    mock_n8n_service.delete_workflow.assert_called_once_with(123)

@pytest.mark.asyncio
async def test_execute_mantra_workflow(client, test_mantra, test_user, db_session, mock_n8n_service):
    """Test executing a mantra workflow."""
    # Create an installation first
    installation = MantraInstallation(
        mantra_id=test_mantra.id,
        user_id=test_mantra.user_id,
        n8n_workflow_id=123,
        status="active"
    )
    db_session.add(installation)
    await db_session.commit()
    await db_session.refresh(installation)

    # Set session data using cookies
    session_data = {
        "user": {
            "id": str(test_user.id),  # Convert UUID to string
            "email": test_user.email,
            "name": test_user.name
        }
    }
    client.cookies.set("session", json.dumps(session_data))

    # Mock N8nService with specific response
    mock_n8n_service.execute_workflow.return_value = {
        "success": True,
        "result": {
            "output": "test",
            "execution_id": "test-execution"
        }
    }

    # Execute workflow using the correct endpoint
    response = client.post(
        f"/api/mantras/installations/{installation.id}/execute",
        json={"trigger": {"email": "test@example.com"}}
    )
    assert response.status_code == 200
    assert response.json()["success"] is True
    assert "execution_id" in response.json()["result"]

@pytest.mark.asyncio
async def test_error_handling_flows(client, test_mantra, mock_n8n_service):
    """Test error handling in various scenarios."""
    # Test invalid installation ID format
    response = client.post(
        "/api/mantras/installations/not-a-uuid/execute",
        json={
            "email": "test@example.com",
            "preferredTime": "2024-01-01T10:00:00Z"
        }
    )
    assert response.status_code == 422  # Validation error for invalid UUID format
    
    # Test non-existent installation ID
    response = client.post(
        "/api/mantras/installations/00000000-0000-0000-0000-000000000000/execute",
        json={
            "email": "test@example.com",
            "preferredTime": "2024-01-01T10:00:00Z"
        }
    )
    assert response.status_code == 404
    
    # Test invalid workflow format
    test_mantra.workflow_json = {}  # Empty workflow
    response = client.post(
        f"/api/mantras/{test_mantra.id}/install?user_id={test_mantra.user_id}",
        json={}
    )
    assert response.status_code == 400
    assert "Invalid workflow format" in response.json()["detail"] 