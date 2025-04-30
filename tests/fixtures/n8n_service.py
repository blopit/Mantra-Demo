"""
N8N service mock fixtures for testing.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from src.services.n8n_service import N8nService

@pytest.fixture
def mock_n8n_service():
    """Mock N8nService for testing."""
    mock = AsyncMock(spec=N8nService)
    
    # Mock create_workflow
    mock.create_workflow = AsyncMock(return_value={
        "id": 123,
        "name": "Test Workflow"
    })
    
    # Mock activate_workflow
    mock.activate_workflow = AsyncMock()
    
    # Mock deactivate_workflow
    mock.deactivate_workflow = AsyncMock()
    
    # Mock delete_workflow
    mock.delete_workflow = AsyncMock()
    
    # Mock execute_workflow
    mock.execute_workflow = AsyncMock(return_value={
        "execution_id": "test-execution",
        "status": "success",
        "data": "test output"
    })
    
    # Mock parse_workflow
    mock.parse_workflow = MagicMock()
    
    return mock 