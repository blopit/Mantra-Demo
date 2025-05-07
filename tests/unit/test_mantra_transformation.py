"""
Unit tests for mantra workflow transformation.
Tests the conversion of webhook/trigger nodes to executeWorkflow nodes.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from src.services.mantra_service import MantraService
from src.services.n8n_service import N8nService
from src.models.mantra import Mantra
from src.models.users import Users
from fastapi import HTTPException

@pytest_asyncio.fixture
async def mock_db_session():
    """Create a mock database session."""
    session = AsyncMock(spec=AsyncSession)
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.rollback = AsyncMock()
    return session

@pytest_asyncio.fixture
async def mock_n8n_service():
    """Create a mock N8N service."""
    service = AsyncMock(spec=N8nService)
    service._validate_workflow_structure = MagicMock()
    return service

@pytest_asyncio.fixture
async def mantra_service(mock_db_session, mock_n8n_service):
    """Create a MantraService instance with mocked dependencies."""
    return MantraService(mock_db_session, mock_n8n_service)

@pytest_asyncio.fixture
async def test_user():
    """Create a test user."""
    return Users(
        id="test_user_id",
        email="test@example.com",
        name="Test User",
        is_active=True
    )

@pytest.mark.asyncio
async def test_webhook_transformation(mantra_service, test_user, mock_db_session):
    """Test that webhook nodes are properly transformed to executeWorkflow nodes."""
    # Setup test data
    webhook_workflow = {
        "nodes": [
            {
                "id": "1",
                "type": "n8n-nodes-base.webhook",
                "name": "Webhook Trigger",
                "parameters": {
                    "path": "onboarding",
                    "responseMode": "responseNode",
                    "options": {}
                }
            },
            {
                "id": "2",
                "type": "gmail",
                "name": "Send Email",
                "parameters": {
                    "operation": "sendEmail",
                    "to": "test@example.com",
                    "subject": "Test Subject",
                    "text": "Test Content"
                }
            }
        ],
        "connections": {
            "Webhook Trigger": {
                "main": [["Send Email", 0]]
            }
        }
    }

    # Mock database queries
    mock_db_session.execute.return_value.scalar_one_or_none.return_value = test_user

    # Create the mantra
    mantra = await mantra_service.create_mantra(
        name="Test Mantra",
        description="Test Description",
        workflow_json=webhook_workflow,
        user_id=test_user.id
    )

    # Verify the transformation
    transformed_nodes = mantra.workflow_json["nodes"]
    
    # Should only have one trigger node
    trigger_nodes = [
        node for node in transformed_nodes 
        if node["type"] == "n8n-nodes-base.executeWorkflowTrigger"
    ]
    assert len(trigger_nodes) == 1
    trigger_node = trigger_nodes[0]
    
    assert trigger_node["name"] == "When Executed by Another Workflow"
    assert trigger_node["typeVersion"] >= 1

@pytest.mark.asyncio
async def test_multiple_trigger_transformation(mantra_service, test_user, mock_db_session):
    """Test that multiple trigger nodes are properly transformed."""
    # Setup test data with multiple triggers
    multi_trigger_workflow = {
        "nodes": [
            {
                "id": "1",
                "type": "n8n-nodes-base.webhook",
                "name": "Webhook Trigger",
                "parameters": {
                    "path": "onboarding",
                    "responseMode": "responseNode"
                }
            },
            {
                "id": "2",
                "type": "n8n-nodes-base.scheduleTrigger",
                "name": "Schedule Trigger",
                "parameters": {
                    "interval": [{"hour": 1}]
                }
            },
            {
                "id": "3",
                "type": "gmail",
                "name": "Send Email",
                "parameters": {
                    "operation": "sendEmail",
                    "to": "test@example.com"
                }
            }
        ],
        "connections": {
            "Webhook Trigger": {
                "main": [["Send Email", 0]]
            },
            "Schedule Trigger": {
                "main": [["Send Email", 0]]
            }
        }
    }

    # Mock database queries
    mock_db_session.execute.return_value.scalar_one_or_none.return_value = test_user

    # Create the mantra
    mantra = await mantra_service.create_mantra(
        name="Test Mantra",
        description="Test Description",
        workflow_json=multi_trigger_workflow,
        user_id=test_user.id
    )

    # Verify all triggers were transformed
    transformed_nodes = mantra.workflow_json["nodes"]
    
    # Should only have one trigger node
    trigger_nodes = [
        node for node in transformed_nodes 
        if node["type"] == "n8n-nodes-base.executeWorkflowTrigger"
    ]
    assert len(trigger_nodes) == 1
    trigger_node = trigger_nodes[0]
    
    assert trigger_node["name"] == "When Executed by Another Workflow"
    assert trigger_node["typeVersion"] >= 1

@pytest.mark.asyncio
async def test_non_trigger_nodes_preserved(mantra_service, test_user, mock_db_session):
    """Test that non-trigger nodes are preserved during transformation."""
    # Setup test data with no triggers
    no_trigger_workflow = {
        "nodes": [
            {
                "id": "1",
                "type": "n8n-nodes-base.gmail",
                "name": "Send Email",
                "parameters": {
                    "operation": "sendEmail",
                    "to": "test@example.com"
                }
            },
            {
                "id": "2",
                "type": "n8n-nodes-base.googleCalendar",
                "name": "Create Event",
                "parameters": {
                    "operation": "createEvent",
                    "calendar": "primary"
                }
            }
        ],
        "connections": {
            "Send Email": {
                "main": [["Create Event", 0]]
            }
        }
    }

    # Mock database queries
    mock_db_session.execute.return_value.scalar_one_or_none.return_value = test_user

    # Create the mantra
    mantra = await mantra_service.create_mantra(
        name="Test Mantra",
        description="Test Description",
        workflow_json=no_trigger_workflow,
        user_id=test_user.id
    )

    # Verify non-trigger nodes were preserved
    transformed_nodes = mantra.workflow_json["nodes"]
    
    # Should have exactly one trigger node (our default one)
    trigger_nodes = [
        node for node in transformed_nodes 
        if node["type"] == "n8n-nodes-base.executeWorkflowTrigger"
    ]
    assert len(trigger_nodes) == 1
    trigger_node = trigger_nodes[0]
    assert trigger_node["name"] == "When Executed by Another Workflow"
    
    # Original nodes should be preserved
    email_node = next(node for node in transformed_nodes if node["id"] == "1")
    calendar_node = next(node for node in transformed_nodes if node["id"] == "2")
    
    assert email_node["type"] == "n8n-nodes-base.gmail"
    assert calendar_node["type"] == "n8n-nodes-base.googleCalendar" 