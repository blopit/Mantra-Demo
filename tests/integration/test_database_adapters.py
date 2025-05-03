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
from sqlalchemy import select

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
    }

@pytest.fixture
def test_mantra(workflow_json) -> Mantra:
    """Create a test mantra."""
    return Mantra(
        id=str(uuid.uuid4()),
        name="Test Mantra",
        description="Test Description",
        workflow_json=workflow_json,
        is_active=True
    )

@pytest.fixture
def test_installation(test_mantra) -> MantraInstallation:
    """Create a test mantra installation."""
    return MantraInstallation(
        id=str(uuid.uuid4()),
        mantra_id=test_mantra.id,
        user_id=str(uuid.uuid4()),
        status="installed",
        config={"test": "config"},
        n8n_workflow_id=123
    )

@pytest_asyncio.fixture
async def sqlite_adapter() -> DatabaseAdapter:
    """Create a SQLite adapter for testing.
    
    This fixture:
    1. Creates an in-memory SQLite database
    2. Initializes the database with all tables
    3. Provides the adapter to the test
    4. Closes the adapter after the test
    """
    adapter = SQLiteAdapter("sqlite+aiosqlite:///:memory:")  # Use in-memory database
    await adapter.init()
    
    # Create all tables
    async with adapter.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield adapter
    
    # Drop all tables and close
    async with adapter.engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await adapter.close()

@pytest_asyncio.fixture
async def postgres_adapter() -> DatabaseAdapter:
    """Create a PostgreSQL adapter for testing if DATABASE_URL is available."""
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL not set")
    
    adapter = PostgresAdapter(database_url)
    await adapter.init()
    
    # Create all tables
    async with adapter.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield adapter
    
    # Drop all tables and close
    async with adapter.engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await adapter.close()

@pytest.mark.asyncio
async def test_sqlite_json_handling(db_session, test_mantra):
    """Test JSON data handling in SQLite."""
    # Add test mantra
    db_session.add(test_mantra)
    await db_session.commit()
    await db_session.refresh(test_mantra)
    
    # Query the mantra
    query = select(Mantra).where(Mantra.id == test_mantra.id)
    result = await db_session.execute(query)
    mantra = result.scalar_one()
    
    # Verify JSON data
    assert mantra.workflow_json["name"] == "Test Workflow"
    assert len(mantra.workflow_json["nodes"]) == 1
    assert mantra.workflow_json["nodes"][0]["type"] == "n8n-nodes-base.emailSend"

@pytest.mark.asyncio
async def test_sqlite_crud_operations(db_session, test_mantra, test_installation):
    """Test CRUD operations in SQLite."""
    # Create
    db_session.add(test_mantra)
    db_session.add(test_installation)
    await db_session.commit()
    
    # Read
    query = select(Mantra).where(Mantra.id == test_mantra.id)
    result = await db_session.execute(query)
    mantra = result.scalar_one()
    assert mantra.name == "Test Mantra"
    
    query = select(MantraInstallation).where(MantraInstallation.id == test_installation.id)
    result = await db_session.execute(query)
    installation = result.scalar_one()
    assert installation.status == "installed"
    
    # Update
    mantra.name = "Updated Mantra"
    installation.status = "updated"
    await db_session.commit()
    await db_session.refresh(mantra)
    await db_session.refresh(installation)
    assert mantra.name == "Updated Mantra"
    assert installation.status == "updated"
    
    # Delete
    await db_session.delete(installation)
    await db_session.delete(mantra)
    await db_session.commit()
    
    # Verify deletion
    query = select(Mantra).where(Mantra.id == test_mantra.id)
    result = await db_session.execute(query)
    assert result.scalar_one_or_none() is None
    
    query = select(MantraInstallation).where(MantraInstallation.id == test_installation.id)
    result = await db_session.execute(query)
    assert result.scalar_one_or_none() is None

@pytest.mark.asyncio
async def test_sqlite_list_and_filter(db_session, test_mantra):
    """Test listing and filtering in SQLite."""
    # Create multiple mantras
    mantras = []
    for i in range(3):
        mantra = Mantra(
            id=str(uuid.uuid4()),
            name=f"Test Mantra {i}",
            description=f"Test Description {i}",
            workflow_json={"name": f"Workflow {i}"},
            is_active=i % 2 == 0
        )
        mantras.append(mantra)
        db_session.add(mantra)
    await db_session.commit()
    
    # List all mantras
    query = select(Mantra)
    result = await db_session.execute(query)
    all_mantras = result.scalars().all()
    assert len(all_mantras) == 3
    
    # Filter by is_active
    query = select(Mantra).where(Mantra.is_active == True)
    result = await db_session.execute(query)
    active_mantras = result.scalars().all()
    assert len(active_mantras) == 2
    
    # Filter by name
    query = select(Mantra).where(Mantra.name.like("Test Mantra 1"))
    result = await db_session.execute(query)
    filtered_mantras = result.scalars().all()
    assert len(filtered_mantras) == 1
    assert filtered_mantras[0].name == "Test Mantra 1"

@pytest.mark.asyncio
async def test_sqlite_mantra_installation(db_session, test_mantra, test_installation):
    """Test mantra installation relationships in SQLite."""
    # Create mantra and installation
    db_session.add(test_mantra)
    db_session.add(test_installation)
    await db_session.commit()
    
    # Query installation with mantra relationship
    query = select(MantraInstallation).where(MantraInstallation.id == test_installation.id)
    result = await db_session.execute(query)
    installation = result.scalar_one()
    
    # Verify relationships
    assert installation.mantra_id == test_mantra.id
    assert installation.status == "installed"
    assert installation.config == {"test": "config"}
    assert installation.n8n_workflow_id == 123

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