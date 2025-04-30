"""
Integration tests for the MantraService class.

These tests verify the integration between MantraService and its dependencies,
including database operations and n8n workflow management.
"""

import pytest
import pytest_asyncio
from uuid import UUID, uuid4
from unittest.mock import AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.services.mantra_service import MantraService
from src.models.mantra import Mantra, MantraInstallation
from src.exceptions import MantraNotFoundError, MantraAlreadyInstalledError

@pytest_asyncio.fixture
async def n8n_service():
    """Mock n8n service with async methods."""
    mock = AsyncMock()
    mock.create_workflow = AsyncMock(return_value=123)  # Mock workflow ID
    mock.activate_workflow = AsyncMock()
    mock.deactivate_workflow = AsyncMock()
    mock.delete_workflow = AsyncMock()
    return mock

@pytest_asyncio.fixture
async def mantra_service(db_session, n8n_service):
    """Create MantraService instance with mocked dependencies."""
    return MantraService(db_session, n8n_service)

@pytest_asyncio.fixture
async def test_mantra(db_session: AsyncSession):
    """Create a test mantra in the database."""
    mantra = Mantra(
        id=uuid4(),
        name="Test Mantra",
        description="Test Description",
        workflow_json={"nodes": [], "connections": {}},
        user_id="test_user",
        is_active=True
    )
    db_session.add(mantra)
    await db_session.commit()
    await db_session.refresh(mantra)
    return mantra

@pytest.mark.asyncio
async def test_install_mantra_success(mantra_service, test_mantra):
    """Test successful mantra installation."""
    # Install the mantra
    installation = await mantra_service.install_mantra(test_mantra.id, "test_user")
    
    # Verify installation record
    assert installation.mantra_id == test_mantra.id
    assert installation.user_id == "test_user"
    assert installation.n8n_workflow_id == 123  # From mock n8n service
    
    # Verify n8n service calls
    mantra_service.n8n_service.create_workflow.assert_called_once_with(test_mantra.workflow_json)
    mantra_service.n8n_service.activate_workflow.assert_called_once_with(123)

@pytest.mark.asyncio
async def test_install_mantra_not_found(mantra_service):
    """Test installing non-existent mantra."""
    with pytest.raises(MantraNotFoundError):
        await mantra_service.install_mantra(uuid4(), "test_user")

@pytest.mark.asyncio
async def test_install_mantra_already_installed(mantra_service, test_mantra, db_session):
    """Test installing already installed mantra."""
    # Create existing installation
    installation = MantraInstallation(
        mantra_id=test_mantra.id,
        user_id="test_user",
        n8n_workflow_id=456
    )
    db_session.add(installation)
    await db_session.commit()
    
    # Attempt to install again
    with pytest.raises(MantraAlreadyInstalledError):
        await mantra_service.install_mantra(test_mantra.id, "test_user")

@pytest.mark.asyncio
async def test_uninstall_mantra_success(mantra_service, test_mantra, db_session):
    """Test successful mantra uninstallation."""
    # Create installation
    installation = MantraInstallation(
        mantra_id=test_mantra.id,
        user_id="test_user",
        n8n_workflow_id=789
    )
    db_session.add(installation)
    await db_session.commit()
    await db_session.refresh(installation)

    # Uninstall the mantra
    await mantra_service.uninstall_mantra(installation.id, "test_user")

    # Verify installation was deleted
    result = await db_session.execute(
        select(MantraInstallation).where(MantraInstallation.id == installation.id)
    )
    assert result.scalar_one_or_none() is None

@pytest.mark.asyncio
async def test_uninstall_mantra_not_found(mantra_service):
    """Test uninstalling non-existent mantra."""
    with pytest.raises(MantraNotFoundError):
        await mantra_service.uninstall_mantra(uuid4(), "test_user")

@pytest.mark.asyncio
async def test_uninstall_mantra_not_installed(mantra_service, test_mantra):
    """Test uninstalling not installed mantra."""
    with pytest.raises(MantraNotFoundError):
        await mantra_service.uninstall_mantra(test_mantra.id, "test_user") 