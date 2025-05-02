"""
Integration tests for database adapters.

These tests verify that:
1. Both SQLite and PostgreSQL adapters work correctly
2. JSON data is handled properly in both databases
3. Database operations work as expected
4. Connection management works correctly
"""

import os
import pytest
import pytest_asyncio
from typing import Dict, Any
import json
from datetime import datetime, timezone
import uuid

from src.adapters.database import DatabaseAdapter
from src.adapters.database.sqlite import SQLiteAdapter
from src.adapters.database.postgres import PostgresAdapter
from src.models.mantra import Mantra, MantraInstallation
from src.models.base import Base

@pytest.fixture
def workflow_json() -> Dict[str, Any]:
    """Test workflow JSON data."""
    return {
        "name": "Test Workflow",
        "nodes": [
            {
                "id": "1",
                "type": "n8n-nodes-base.emailSend",
                "parameters": {
                    "to": "test@example.com",
                    "subject": "Test Email",
                    "text": "This is a test email"
                }
            }
        ],
        "connections": {
            "node1": {
                "main": [[{"node": "2", "type": "main", "index": 0}]]
            }
        }
    }

@pytest_asyncio.fixture
async def sqlite_adapter() -> DatabaseAdapter:
    """Create a SQLite adapter for testing."""
    adapter = SQLiteAdapter("sqlite+aiosqlite://")  # Use in-memory database
    await adapter.init()
    yield adapter
    await adapter.close()

@pytest_asyncio.fixture
async def postgres_adapter() -> DatabaseAdapter:
    """Create a PostgreSQL adapter for testing if DATABASE_URL is available."""
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL not set")
    
    adapter = PostgresAdapter(database_url)
    await adapter.init()
    yield adapter
    await adapter.close()

@pytest.mark.asyncio
async def test_sqlite_json_handling(sqlite_adapter: DatabaseAdapter, workflow_json: Dict[str, Any]):
    """Test JSON data handling in SQLite."""
    # Create a mantra with JSON data
    mantra_data = {
        "id": uuid.uuid4(),
        "name": "Test Mantra",
        "description": "Test Description",
        "workflow_json": workflow_json,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    
    # Create mantra
    mantra = await sqlite_adapter.create(Mantra, mantra_data)
    assert mantra.id == mantra_data["id"]
    assert mantra.workflow_json == workflow_json
    
    # Retrieve mantra
    retrieved = await sqlite_adapter.get(Mantra, mantra.id)
    assert retrieved is not None
    assert retrieved.workflow_json == workflow_json
    
    # Update mantra
    new_workflow = workflow_json.copy()
    new_workflow["name"] = "Updated Workflow"
    await sqlite_adapter.update(Mantra, mantra.id, {"workflow_json": new_workflow})
    
    # Verify update
    updated = await sqlite_adapter.get(Mantra, mantra.id)
    assert updated is not None
    assert updated.workflow_json["name"] == "Updated Workflow"

@pytest.mark.asyncio
async def test_sqlite_crud_operations(sqlite_adapter: DatabaseAdapter):
    """Test basic CRUD operations in SQLite."""
    # Create
    mantra_data = {
        "id": uuid.uuid4(),
        "name": "Test Mantra",
        "description": "Test Description",
        "workflow_json": {"test": "data"},
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    mantra = await sqlite_adapter.create(Mantra, mantra_data)
    assert mantra.id == mantra_data["id"]
    
    # Read
    retrieved = await sqlite_adapter.get(Mantra, mantra.id)
    assert retrieved is not None
    assert retrieved.name == "Test Mantra"
    
    # Update
    await sqlite_adapter.update(Mantra, mantra.id, {"name": "Updated Mantra"})
    updated = await sqlite_adapter.get(Mantra, mantra.id)
    assert updated is not None
    assert updated.name == "Updated Mantra"
    
    # Delete
    deleted = await sqlite_adapter.delete(Mantra, mantra.id)
    assert deleted is True
    
    # Verify deletion
    not_found = await sqlite_adapter.get(Mantra, mantra.id)
    assert not_found is None

@pytest.mark.asyncio
async def test_sqlite_list_and_filter(sqlite_adapter: DatabaseAdapter):
    """Test list and filter operations in SQLite."""
    # Create test data
    mantras = []
    for i in range(3):
        mantra_data = {
            "id": uuid.uuid4(),
            "name": f"Mantra {i}",
            "description": f"Description {i}",
            "workflow_json": {"test": f"data {i}"},
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        mantra = await sqlite_adapter.create(Mantra, mantra_data)
        mantras.append(mantra)
    
    # List all
    all_mantras = await sqlite_adapter.list(Mantra)
    assert len(all_mantras) == 3
    
    # Filter
    filtered = await sqlite_adapter.list(Mantra, {"name": "Mantra 1"})
    assert len(filtered) == 1
    assert filtered[0].name == "Mantra 1"
    
    # Count
    count = await sqlite_adapter.count(Mantra)
    assert count == 3
    
    # Exists
    exists = await sqlite_adapter.exists(Mantra, {"name": "Mantra 1"})
    assert exists is True
    
    not_exists = await sqlite_adapter.exists(Mantra, {"name": "Nonexistent"})
    assert not_exists is False

@pytest.mark.asyncio
async def test_sqlite_mantra_installation(sqlite_adapter: DatabaseAdapter, workflow_json: Dict[str, Any]):
    """Test mantra installation with JSON data in SQLite."""
    # Create a mantra first
    mantra_data = {
        "id": uuid.uuid4(),
        "name": "Test Mantra",
        "description": "Test Description",
        "workflow_json": workflow_json,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    mantra = await sqlite_adapter.create(Mantra, mantra_data)
    
    # Create installation
    installation_data = {
        "id": uuid.uuid4(),
        "mantra_id": mantra.id,
        "user_id": uuid.uuid4(),
        "installed_at": datetime.now(timezone.utc),
        "status": "pending",
        "config": {"test": "config"},
        "n8n_workflow_id": None
    }
    
    installation = await sqlite_adapter.create(MantraInstallation, installation_data)
    assert installation.id == installation_data["id"]
    assert installation.config == {"test": "config"}
    
    # Update installation
    new_config = {"test": "updated_config"}
    await sqlite_adapter.update(MantraInstallation, installation.id, {
        "config": new_config,
        "status": "installed"
    })
    
    # Verify update
    updated = await sqlite_adapter.get(MantraInstallation, installation.id)
    assert updated is not None
    assert updated.config == new_config
    assert updated.status == "installed"

# Only run PostgreSQL tests if TEST_DATABASE_URL is set
@pytest.mark.asyncio
@pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="TEST_DATABASE_URL not set")
async def test_postgres_json_handling(postgres_adapter: DatabaseAdapter, workflow_json: Dict[str, Any]):
    """Test JSON data handling in PostgreSQL."""
    # Create a mantra with JSON data
    mantra_data = {
        "id": uuid.uuid4(),
        "name": "Test Mantra",
        "description": "Test Description",
        "workflow_json": workflow_json,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    
    # Create mantra
    mantra = await postgres_adapter.create(Mantra, mantra_data)
    assert mantra.id == mantra_data["id"]
    assert mantra.workflow_json == workflow_json
    
    # Retrieve mantra
    retrieved = await postgres_adapter.get(Mantra, mantra.id)
    assert retrieved is not None
    assert retrieved.workflow_json == workflow_json
    
    # Update mantra
    new_workflow = workflow_json.copy()
    new_workflow["name"] = "Updated Workflow"
    await postgres_adapter.update(Mantra, mantra.id, {"workflow_json": new_workflow})
    
    # Verify update
    updated = await postgres_adapter.get(Mantra, mantra.id)
    assert updated is not None
    assert updated.workflow_json["name"] == "Updated Workflow" 