"""Tests for mantra installation functionality."""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from src.services.mantra_service import MantraService
from src.services.n8n_service import N8nService
from src.models.mantra import Mantra, MantraInstallation
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

@pytest.fixture
def mock_db_session():
    """Mock database session for testing."""
    mock = AsyncMock(spec=AsyncSession)
    # Create a mock result object that returns values directly
    mock_result = Mock()
    mock_result.scalar_one_or_none = Mock()
    # Make execute return the mock result
    mock.execute = AsyncMock(return_value=mock_result)
    return mock

@pytest.fixture
def mock_n8n_service():
    """Mock N8N service for testing."""
    mock = AsyncMock(spec=N8nService)
    return mock

@pytest.fixture
def sample_mantra():
    """Create a sample mantra for testing."""
    return Mantra(
        id="test-mantra-id",
        name="Test Mantra",
        description="Test mantra description",
        workflow_json={"nodes": [], "connections": {}},
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        is_active=True,
        user_id="test-user-id"
    )

@pytest.fixture
def mantra_service(mock_db_session, mock_n8n_service):
    """Create a MantraService instance with mocked dependencies."""
    return MantraService(db_session=mock_db_session, n8n_service=mock_n8n_service)

@pytest.mark.asyncio
async def test_install_mantra_success(mantra_service, sample_mantra, mock_n8n_service, mock_db_session):
    """Test successful mantra installation."""
    # Setup
    user_id = "test-user-id"
    mock_n8n_service.create_workflow.return_value = {"id": "n8n-workflow-id"}
    mock_n8n_service.activate_workflow.return_value = True
    
    # Mock database queries
    mock_db_session.execute.return_value.scalar_one_or_none.side_effect = [
        sample_mantra,  # First call returns the mantra
        None  # Second call returns no existing installation
    ]
    
    # Execute
    result = await mantra_service.install_mantra(
        mantra_id=sample_mantra.id,
        user_id=user_id
    )
    
    # Assert
    assert isinstance(result, MantraInstallation)
    assert result.mantra_id == sample_mantra.id
    assert result.user_id == user_id
    assert result.status == "active"
    assert result.n8n_workflow_id == "n8n-workflow-id"
    
    # Verify N8N service calls
    mock_n8n_service.create_workflow.assert_awaited_once_with(sample_mantra.workflow_json)
    mock_n8n_service.activate_workflow.assert_awaited_once_with("n8n-workflow-id")

@pytest.mark.asyncio
async def test_install_mantra_already_installed(mantra_service, sample_mantra, mock_db_session):
    """Test mantra installation when already installed."""
    # Setup
    user_id = "test-user-id"
    existing_installation = MantraInstallation(
        id="test-installation-id",
        mantra_id=sample_mantra.id,
        user_id=user_id,
        installed_at=datetime.utcnow(),
        status="active",
        n8n_workflow_id="existing-workflow-id"
    )
    
    # Mock database queries
    mock_db_session.execute.return_value.scalar_one_or_none.side_effect = [
        sample_mantra,  # First call returns the mantra
        existing_installation  # Second call returns existing installation
    ]
    
    # Execute & Assert
    with pytest.raises(HTTPException) as exc_info:
        await mantra_service.install_mantra(
            mantra_id=sample_mantra.id,
            user_id=user_id
        )
    assert exc_info.value.status_code == 400
    assert "already installed" in exc_info.value.detail

@pytest.mark.asyncio
async def test_install_mantra_n8n_error(mantra_service, sample_mantra, mock_n8n_service, mock_db_session):
    """Test mantra installation when N8N workflow creation fails."""
    # Setup
    user_id = "test-user-id"
    mock_n8n_service.create_workflow.side_effect = Exception("N8N API error")
    
    # Mock database queries
    mock_db_session.execute.return_value.scalar_one_or_none.side_effect = [
        sample_mantra,  # First call returns the mantra
        None  # Second call returns no existing installation
    ]
    
    # Execute & Assert
    with pytest.raises(HTTPException) as exc_info:
        await mantra_service.install_mantra(
            mantra_id=sample_mantra.id,
            user_id=user_id
        )
    assert exc_info.value.status_code == 500
    assert "N8N API error" in exc_info.value.detail
    
    # Verify N8N service calls
    mock_n8n_service.create_workflow.assert_awaited_once_with(sample_mantra.workflow_json)
    mock_n8n_service.activate_workflow.assert_not_called() 