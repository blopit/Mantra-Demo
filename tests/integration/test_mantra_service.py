"""
Integration tests for the mantra service.

These tests verify that:
1. Mantra installation works correctly
2. Error handling is proper
3. N8N service integration functions as expected
4. Database operations are successful
5. Network conditions are properly handled
"""

import pytest
import pytest_asyncio
from uuid import UUID, uuid4
from unittest.mock import AsyncMock, patch, Mock, MagicMock
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.engine import Result
from src.services.mantra_service import MantraService
from src.services.n8n_service import N8nService
from src.models.mantra import Mantra, MantraInstallation
from src.exceptions import MantraNotFoundError, MantraAlreadyInstalledError
from fastapi import HTTPException, status
from datetime import datetime
from tests.fixtures.n8n_service import MockResponse, MockAsyncClient

@pytest_asyncio.fixture
async def n8n_service():
    """Create a mock N8N service with proper response format."""
    mock = AsyncMock()
    mock.create_workflow = AsyncMock(return_value={"data": {"id": 123}})
    mock.activate_workflow = AsyncMock()
    mock.deactivate_workflow = AsyncMock()
    mock.delete_workflow = AsyncMock()
    return mock

@pytest_asyncio.fixture
async def mantra_service(db_session, n8n_service):
    """Create MantraService instance with mocked dependencies."""
    return MantraService(db_session, n8n_service)

@pytest.fixture
def test_mantra() -> Mantra:
    """Create a test mantra."""
    return Mantra(
        id="test_mantra_id",
        name="Test Mantra",
        description="Test Description",
        workflow_json={
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
        },
        is_active=True
    )

@pytest.fixture
def test_installation(test_mantra) -> MantraInstallation:
    """Create a test mantra installation."""
    return MantraInstallation(
        id="test_installation_id",
        mantra_id=test_mantra.id,
        user_id="test_user_id",
        status="installed",
        config={"test": "config"},
        n8n_workflow_id=123
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
async def test_install_mantra_success(mantra_service, test_mantra, db_session):
    """Test successful mantra installation."""
    # Add test mantra to database
    db_session.add(test_mantra)
    await db_session.commit()
    
    # Install mantra
    installation = await mantra_service.install_mantra(test_mantra.id, "test_user_id")
    
    # Verify installation
    assert installation.mantra_id == test_mantra.id
    assert installation.user_id == "test_user_id"
    assert installation.status == "installed"
    assert installation.n8n_workflow_id == 123

@pytest.mark.asyncio
async def test_install_mantra_with_network_error(mantra_service, test_mantra, db_session):
    """Test mantra installation with network error."""
    # Add test mantra to database
    db_session.add(test_mantra)
    await db_session.commit()
    
    # Create mock N8N service with network error
    mock_n8n = AsyncMock()
    mock_n8n.create_workflow = AsyncMock(side_effect=httpx.TimeoutError("Connection timeout"))
    mantra_service.n8n_service = mock_n8n
    
    # Try to install
    with pytest.raises(HTTPException) as exc_info:
        await mantra_service.install_mantra(test_mantra.id, "test_user_id")
    assert exc_info.value.status_code == 503
    assert "Service unavailable" in str(exc_info.value.detail)
    
    # Verify no installation was created
    query = select(MantraInstallation).where(
        MantraInstallation.mantra_id == test_mantra.id,
        MantraInstallation.user_id == "test_user_id"
    )
    result = await db_session.execute(query)
    installation = result.scalar_one_or_none()
    assert installation is None

@pytest.mark.asyncio
async def test_install_mantra_with_retry_success(mantra_service, test_mantra, db_session):
    """Test mantra installation with retry after failure."""
    # Add test mantra to database
    db_session.add(test_mantra)
    await db_session.commit()
    
    # Create mock N8N service that fails once then succeeds
    mock_n8n = AsyncMock()
    mock_n8n.create_workflow = AsyncMock(side_effect=[
        httpx.TimeoutError("Connection timeout"),
        {"data": {"id": 123}}
    ])
    mock_n8n.activate_workflow = AsyncMock()
    mantra_service.n8n_service = mock_n8n
    
    # Install mantra (should succeed after retry)
    installation = await mantra_service.install_mantra(test_mantra.id, "test_user_id")
    
    # Verify installation
    assert installation.mantra_id == test_mantra.id
    assert installation.status == "installed"
    assert installation.n8n_workflow_id == 123

@pytest.mark.asyncio
async def test_install_mantra_with_invalid_workflow(mantra_service, test_mantra, db_session):
    """Test mantra installation with invalid workflow JSON."""
    # Modify test mantra to have invalid workflow JSON
    test_mantra.workflow_json = {"invalid": "format"}
    db_session.add(test_mantra)
    await db_session.commit()
    
    # Try to install
    with pytest.raises(HTTPException) as exc_info:
        await mantra_service.install_mantra(test_mantra.id, "test_user_id")
    assert exc_info.value.status_code == 400
    assert "Invalid workflow format" in str(exc_info.value.detail)

@pytest.mark.asyncio
async def test_uninstall_mantra_with_network_error(mantra_service, test_mantra, test_installation, db_session):
    """Test mantra uninstallation with network error."""
    # Add test data to database
    db_session.add(test_mantra)
    db_session.add(test_installation)
    await db_session.commit()
    
    # Create mock N8N service with network error
    mock_n8n = AsyncMock()
    mock_n8n.delete_workflow = AsyncMock(side_effect=httpx.TimeoutError("Connection timeout"))
    mantra_service.n8n_service = mock_n8n
    
    # Try to uninstall
    with pytest.raises(HTTPException) as exc_info:
        await mantra_service.uninstall_mantra(test_mantra.id, "test_user_id")
    assert exc_info.value.status_code == 503
    assert "Service unavailable" in str(exc_info.value.detail)
    
    # Verify installation still exists
    query = select(MantraInstallation).where(
        MantraInstallation.mantra_id == test_mantra.id,
        MantraInstallation.user_id == "test_user_id"
    )
    result = await db_session.execute(query)
    installation = result.scalar_one_or_none()
    assert installation is not None

@pytest.mark.asyncio
async def test_uninstall_mantra_with_retry_success(mantra_service, test_mantra, test_installation, db_session):
    """Test mantra uninstallation with retry after failure."""
    # Add test data to database
    db_session.add(test_mantra)
    db_session.add(test_installation)
    await db_session.commit()
    
    # Create mock N8N service that fails once then succeeds
    mock_n8n = AsyncMock()
    mock_n8n.delete_workflow = AsyncMock(side_effect=[
        httpx.TimeoutError("Connection timeout"),
        None
    ])
    mantra_service.n8n_service = mock_n8n
    
    # Uninstall mantra (should succeed after retry)
    await mantra_service.uninstall_mantra(test_mantra.id, "test_user_id")
    
    # Verify installation was deleted
    query = select(MantraInstallation).where(
        MantraInstallation.mantra_id == test_mantra.id,
        MantraInstallation.user_id == "test_user_id"
    )
    result = await db_session.execute(query)
    installation = result.scalar_one_or_none()
    assert installation is None

@pytest.mark.asyncio
async def test_install_mantra_cleanup_on_activation_error(mantra_service, test_mantra, db_session):
    """Test cleanup when workflow activation fails."""
    # Add test mantra to database
    db_session.add(test_mantra)
    await db_session.commit()
    
    # Create mock N8N service that succeeds creation but fails activation
    mock_n8n = AsyncMock()
    mock_n8n.create_workflow = AsyncMock(return_value={"data": {"id": 123}})
    mock_n8n.activate_workflow = AsyncMock(side_effect=HTTPException(
        status_code=500,
        detail="Activation failed"
    ))
    mock_n8n.delete_workflow = AsyncMock()  # Should be called during cleanup
    mantra_service.n8n_service = mock_n8n
    
    # Try to install
    with pytest.raises(HTTPException) as exc_info:
        await mantra_service.install_mantra(test_mantra.id, "test_user_id")
    assert exc_info.value.status_code == 500
    assert "Activation failed" in str(exc_info.value.detail)
    
    # Verify no installation exists and workflow was cleaned up
    query = select(MantraInstallation).where(
        MantraInstallation.mantra_id == test_mantra.id,
        MantraInstallation.user_id == "test_user_id"
    )
    result = await db_session.execute(query)
    installation = result.scalar_one_or_none()
    assert installation is None
    mock_n8n.delete_workflow.assert_called_once_with(123) 