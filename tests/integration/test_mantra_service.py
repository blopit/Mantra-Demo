"""
Integration tests for the MantraService class.

These tests verify the integration between MantraService and its dependencies,
including database operations and n8n workflow management.
"""

import pytest
import pytest_asyncio
from uuid import UUID, uuid4
from unittest.mock import AsyncMock, patch, Mock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.engine import Result
from src.services.mantra_service import MantraService
from src.services.n8n_service import N8nService
from src.models.mantra import Mantra, MantraInstallation
from src.exceptions import MantraNotFoundError, MantraAlreadyInstalledError
from fastapi import HTTPException, status
from datetime import datetime

@pytest_asyncio.fixture
async def n8n_service():
    """Mock n8n service with async methods."""
    mock = AsyncMock()
    mock.create_workflow = AsyncMock(return_value={"id": 123})  # Return dict with id instead of just id
    mock.activate_workflow = AsyncMock()
    mock.deactivate_workflow = AsyncMock()
    mock.delete_workflow = AsyncMock()
    return mock

@pytest_asyncio.fixture
async def mantra_service(db_session, n8n_service):
    """Create MantraService instance with mocked dependencies."""
    return MantraService(db_session, n8n_service)

@pytest.fixture
def test_mantra():
    """Create a test mantra with a valid UUID."""
    return Mantra(
        id=str(uuid4()),  # Use a real UUID
        name="Test Mantra",
        description="Test Description",
        workflow_json={
            "nodes": [
                {
                    "id": "1",
                    "type": "function",
                    "name": "Test Function",
                    "parameters": {
                        "code": "// Test code"
                    }
                }
            ],
            "connections": {}
        }
    )

@pytest.fixture
def mock_n8n_service():
    """Create a mock N8N service."""
    return AsyncMock(spec=N8nService)

@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    session = AsyncMock(spec=AsyncSession)
    session.begin = AsyncMock()
    session.begin.return_value.__aenter__ = AsyncMock()
    session.begin.return_value.__aexit__ = AsyncMock()
    session.execute = AsyncMock()
    session.add = AsyncMock()
    session.flush = AsyncMock()
    session.delete = AsyncMock()
    return session

@pytest.mark.asyncio
async def test_install_mantra_success(mantra_service, test_mantra, mock_db_session, mock_n8n_service):
    """Test successful mantra installation."""
    # Setup mock result for mantra query
    mock_result = MagicMock(spec=Result)
    mock_result.scalar_one_or_none.side_effect = [test_mantra, None]  # Return mantra first, then None for installation check
    mock_db_session.execute.return_value = mock_result

    # Mock N8N service responses
    mock_n8n_service.create_workflow.return_value = {"id": 123}
    mock_n8n_service.activate_workflow.return_value = None

    # Install mantra
    installation = await mantra_service.install_mantra(test_mantra.id, "test_user")

    # Verify installation
    assert installation.mantra_id == test_mantra.id
    assert installation.user_id == "test_user"
    assert installation.n8n_workflow_id == 123
    assert installation.status == "active"

@pytest.mark.asyncio
async def test_install_mantra_not_found(mantra_service, mock_db_session):
    """Test mantra installation when mantra doesn't exist."""
    # Setup mock result to return None
    mock_result = MagicMock(spec=Result)
    mock_result.scalar_one_or_none.return_value = None
    mock_db_session.execute.return_value = mock_result

    # Attempt installation
    with pytest.raises(HTTPException) as exc_info:
        await mantra_service.install_mantra(str(uuid4()), "test_user")  # Use a real UUID

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in exc_info.value.detail

@pytest.mark.asyncio
async def test_install_mantra_already_installed(mantra_service, test_mantra, mock_db_session):
    """Test mantra installation when already installed."""
    # Setup mock results
    mock_result = MagicMock(spec=Result)
    mock_result.scalar_one_or_none.side_effect = [
        test_mantra,  # First call returns the mantra
        MantraInstallation(  # Second call returns existing installation
            mantra_id=test_mantra.id,
            user_id="test_user",
            n8n_workflow_id=123,
            status="active"
        )
    ]
    mock_db_session.execute.return_value = mock_result

    # Attempt installation
    with pytest.raises(HTTPException) as exc_info:
        await mantra_service.install_mantra(test_mantra.id, "test_user")

    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert "already installed" in exc_info.value.detail

@pytest.mark.asyncio
async def test_uninstall_mantra_success(mantra_service, test_mantra, mock_db_session, mock_n8n_service):
    """Test successful mantra uninstallation."""
    # Create test installation
    installation = MantraInstallation(
        id=str(uuid4()),  # Use a real UUID
        mantra_id=test_mantra.id,
        user_id="test_user",
        n8n_workflow_id=123,
        status="active"
    )

    # Setup mock result
    mock_result = MagicMock(spec=Result)
    mock_result.scalar_one_or_none.return_value = installation
    mock_db_session.execute.return_value = mock_result

    # Mock N8N service response
    mock_n8n_service.delete_workflow.return_value = None

    # Uninstall mantra
    await mantra_service.uninstall_mantra(installation.id, "test_user")

    # Verify N8N workflow was deleted
    mock_n8n_service.delete_workflow.assert_called_once_with(123)

@pytest.mark.asyncio
async def test_uninstall_mantra_not_found(mantra_service, mock_db_session):
    """Test mantra uninstallation when installation doesn't exist."""
    # Setup mock result to return None
    mock_result = MagicMock(spec=Result)
    mock_result.scalar_one_or_none.return_value = None
    mock_db_session.execute.return_value = mock_result

    # Attempt uninstallation
    with pytest.raises(HTTPException) as exc_info:
        await mantra_service.uninstall_mantra(str(uuid4()), "test_user")  # Use a real UUID

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in exc_info.value.detail

@pytest.mark.asyncio
async def test_uninstall_mantra_not_installed(mantra_service, test_mantra, mock_db_session):
    """Test mantra uninstallation when not installed by user."""
    # Create test installation for different user
    installation = MantraInstallation(
        id=str(uuid4()),  # Use a real UUID
        mantra_id=test_mantra.id,
        user_id="other_user",  # Different user
        n8n_workflow_id=123,
        status="active"
    )

    # Setup mock result
    mock_result = MagicMock(spec=Result)
    mock_result.scalar_one_or_none.return_value = installation
    mock_db_session.execute.return_value = mock_result

    # Attempt uninstallation
    with pytest.raises(HTTPException) as exc_info:
        await mantra_service.uninstall_mantra(installation.id, "test_user")

    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    assert "not installed by user" in exc_info.value.detail

@pytest.mark.asyncio
async def test_install_mantra_n8n_error_400(mantra_service, test_mantra, mock_db_session, mock_n8n_service):
    """Test mantra installation when N8N returns 400 error."""
    # Setup mock result
    mock_result = MagicMock(spec=Result)
    mock_result.scalar_one_or_none.side_effect = [test_mantra, None]
    mock_db_session.execute.return_value = mock_result

    # Mock N8N service to return 400 error
    mock_n8n_service.create_workflow.side_effect = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid workflow format: Missing required field 'name'"
    )

    # Attempt installation
    with pytest.raises(HTTPException) as exc_info:
        await mantra_service.install_mantra(test_mantra.id, "test_user")

    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert "Invalid workflow format" in exc_info.value.detail

@pytest.mark.asyncio
async def test_install_mantra_n8n_error_500(mantra_service, test_mantra, mock_db_session, mock_n8n_service):
    """Test mantra installation when N8N returns 500 error."""
    # Setup mock result
    mock_result = MagicMock(spec=Result)
    mock_result.scalar_one_or_none.side_effect = [test_mantra, None]
    mock_db_session.execute.return_value = mock_result

    # Mock N8N service to return 500 error
    mock_n8n_service.create_workflow.side_effect = HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Internal server error"
    )

    # Attempt installation
    with pytest.raises(HTTPException) as exc_info:
        await mantra_service.install_mantra(test_mantra.id, "test_user")

    assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "Internal server error" in exc_info.value.detail

@pytest.mark.asyncio
async def test_install_mantra_invalid_workflow_json(mantra_service, test_mantra, mock_db_session):
    """Test mantra installation with invalid workflow JSON."""
    # Modify test mantra to have invalid workflow JSON
    test_mantra.workflow_json = {
        "nodes": "invalid",  # Should be an array
        "connections": {}
    }

    # Setup mock result
    mock_result = MagicMock(spec=Result)
    mock_result.scalar_one_or_none.side_effect = [test_mantra, None]
    mock_db_session.execute.return_value = mock_result

    # Attempt installation
    with pytest.raises(HTTPException) as exc_info:
        await mantra_service.install_mantra(test_mantra.id, "test_user")

    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert "Invalid workflow format" in exc_info.value.detail

@pytest.mark.asyncio
async def test_install_mantra_missing_required_fields(mantra_service, test_mantra, mock_db_session):
    """Test mantra installation with missing required fields in workflow JSON."""
    # Modify test mantra to have missing required fields
    test_mantra.workflow_json = {
        "nodes": [
            {
                "id": "1",
                # Missing type field
                "name": "Send Email",
                "parameters": {}
            }
        ],
        "connections": {}
    }

    # Setup mock result
    mock_result = MagicMock(spec=Result)
    mock_result.scalar_one_or_none.side_effect = [test_mantra, None]
    mock_db_session.execute.return_value = mock_result

    # Attempt installation
    with pytest.raises(HTTPException) as exc_info:
        await mantra_service.install_mantra(test_mantra.id, "test_user")

    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert "must contain 'type'" in exc_info.value.detail

@pytest.mark.asyncio
async def test_install_mantra_with_config(mantra_service, test_mantra, mock_db_session, mock_n8n_service):
    """Test mantra installation with custom configuration."""
    # Setup
    config = {
        "email_template": "custom_template",
        "notification_settings": {
            "enabled": True,
            "frequency": "daily"
        }
    }

    # Setup mock result
    mock_result = MagicMock(spec=Result)
    mock_result.scalar_one_or_none.side_effect = [test_mantra, None]
    mock_db_session.execute.return_value = mock_result

    # Mock N8N service responses
    mock_n8n_service.create_workflow.return_value = {"id": 123}
    mock_n8n_service.activate_workflow.return_value = None

    # Install with config
    installation = await mantra_service.install_mantra(test_mantra.id, "test_user", config)

    # Verify installation
    assert installation.mantra_id == test_mantra.id
    assert installation.user_id == "test_user"
    assert installation.n8n_workflow_id == 123
    assert installation.status == "active"
    assert installation.config == config

@pytest.mark.asyncio
async def test_install_mantra_cleanup_on_activation_error(mantra_service, test_mantra, mock_db_session, mock_n8n_service):
    """Test cleanup when workflow activation fails."""
    # Setup mock result
    mock_result = MagicMock(spec=Result)
    mock_result.scalar_one_or_none.side_effect = [test_mantra, None]
    mock_db_session.execute.return_value = mock_result

    # Mock workflow creation success but activation failure
    mock_n8n_service.create_workflow.return_value = {"id": 123}
    mock_n8n_service.activate_workflow.side_effect = HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Failed to activate workflow"
    )

    # Attempt installation
    with pytest.raises(HTTPException) as exc_info:
        await mantra_service.install_mantra(test_mantra.id, "test_user")

    assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "Failed to activate workflow" in exc_info.value.detail

    # Verify cleanup was called
    mock_n8n_service.delete_workflow.assert_called_once_with(123)

@pytest.mark.asyncio
async def test_install_mantra_with_large_workflow(mantra_service, test_mantra, mock_db_session, mock_n8n_service):
    """Test mantra installation with a large workflow JSON."""
    # Create a large workflow with many nodes
    nodes = []
    for i in range(100):
        nodes.append({
            "id": str(i),
            "type": "function",
            "name": f"Function {i}",
            "parameters": {
                "code": f"// Function {i} code"
            }
        })

    test_mantra.workflow_json = {
        "nodes": nodes,
        "connections": {
            str(i): {"main": [[str(i+1), 0]]} for i in range(99)
        }
    }

    # Setup mock result
    mock_result = MagicMock(spec=Result)
    mock_result.scalar_one_or_none.side_effect = [test_mantra, None]
    mock_db_session.execute.return_value = mock_result

    # Mock N8N service responses
    mock_n8n_service.create_workflow.return_value = {"id": 123}
    mock_n8n_service.activate_workflow.return_value = None

    # Install large workflow
    installation = await mantra_service.install_mantra(test_mantra.id, "test_user")

    # Verify installation
    assert installation.mantra_id == test_mantra.id
    assert installation.user_id == "test_user"
    assert installation.n8n_workflow_id == 123
    assert installation.status == "active" 