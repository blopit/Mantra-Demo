"""
Tests for database configuration and connection handling.

This module tests the database configuration to ensure that it correctly
handles different database types (SQLite and PostgreSQL) and environments
(development, production, testing).
"""

import os
import pytest
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from src.utils.database import get_database_url, get_engine

def test_get_database_url_testing():
    """Test that get_database_url returns in-memory SQLite URL in testing mode."""
    # Set testing environment
    os.environ["TESTING"] = "true"
    
    # Get database URL
    db_url = get_database_url()
    
    # Check that it's an in-memory SQLite URL
    assert db_url == "sqlite+aiosqlite://"
    
    # Clean up
    os.environ.pop("TESTING", None)

def test_get_database_url_development():
    """Test that get_database_url returns development URL in development mode."""
    # Set development environment
    os.environ["ENVIRONMENT"] = "development"
    os.environ["DATABASE_URL_DEV"] = "sqlite+aiosqlite:///test_dev.db"
    
    # Get database URL
    db_url = get_database_url()
    
    # Check that it's the development URL
    assert db_url == "sqlite+aiosqlite:///test_dev.db"
    
    # Clean up
    os.environ.pop("ENVIRONMENT", None)
    os.environ.pop("DATABASE_URL_DEV", None)

def test_get_database_url_production():
    """Test that get_database_url returns production URL in production mode."""
    # Set production environment
    os.environ["ENVIRONMENT"] = "production"
    os.environ["DATABASE_URL"] = "postgresql://user:password@localhost:5432/test_db"
    
    # Get database URL
    db_url = get_database_url()
    
    # Check that it's the production URL
    assert db_url == "postgresql://user:password@localhost:5432/test_db"
    
    # Clean up
    os.environ.pop("ENVIRONMENT", None)
    os.environ.pop("DATABASE_URL", None)

def test_get_database_url_fallback():
    """Test that get_database_url falls back to default SQLite URLs."""
    # Clear environment variables
    for var in ["TESTING", "ENVIRONMENT", "ENV", "DATABASE_URL_DEV", "DATABASE_URL"]:
        if var in os.environ:
            os.environ.pop(var)
    
    # Get database URL (should default to development)
    db_url = get_database_url()
    
    # Check that it's the default development SQLite URL
    assert db_url == "sqlite+aiosqlite:///mantra_dev.db"
    
    # Set production environment without DATABASE_URL
    os.environ["ENVIRONMENT"] = "production"
    
    # Get database URL
    db_url = get_database_url()
    
    # Check that it's the default production SQLite URL
    assert db_url == "sqlite+aiosqlite:///mantra.db"
    
    # Clean up
    os.environ.pop("ENVIRONMENT", None)

def test_engine_configuration_sqlite():
    """Test that the engine is configured correctly for SQLite."""
    # Create engine with SQLite URL
    engine = get_engine("sqlite+aiosqlite:///test.db")
    
    # Check engine configuration
    assert engine.dialect.name == "sqlite"
    
    # Async engines cannot be used for direct queries in this test
    # The actual query execution is tested in integration tests
    assert engine.url.drivername == "sqlite+aiosqlite"

def test_engine_configuration_postgresql():
    """
    Test that the engine is configured correctly for PostgreSQL.
    
    This test is skipped if no PostgreSQL URL is available.
    """
    # Skip if no PostgreSQL URL is available
    postgresql_url = os.environ.get("DATABASE_URL")
    if not postgresql_url or not postgresql_url.startswith("postgresql://"):
        pytest.skip("No PostgreSQL URL available for testing")
    
    # Create engine with PostgreSQL URL
    engine = get_engine(postgresql_url)
    
    # Check engine configuration
    assert engine.dialect.name == "postgresql"
    
    # Check that we can execute a simple query
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            assert result.scalar() == 1
    except SQLAlchemyError as e:
        pytest.fail(f"Failed to execute query on PostgreSQL engine: {e}")

def test_newline_handling_in_database_url():
    """Test that newlines in database URLs are handled correctly."""
    # Set environment variables with newlines
    os.environ["ENVIRONMENT"] = "development"
    os.environ["DATABASE_URL_DEV"] = "sqlite:///test_dev.db\nPORT=8000"
    
    # Get database URL
    db_url = get_database_url()
    
    # Check that newlines are removed
    assert db_url == "sqlite:///test_dev.db"
    
    # Set production environment with newlines
    os.environ["ENVIRONMENT"] = "production"
    os.environ["DATABASE_URL"] = "postgresql://user:password@localhost:5432/test_db\nSOME_OTHER_VAR=value"
    
    # Get database URL
    db_url = get_database_url()
    
    # Check that newlines are removed
    assert db_url == "postgresql://user:password@localhost:5432/test_db"
    
    # Clean up
    os.environ.pop("ENVIRONMENT", None)
    os.environ.pop("DATABASE_URL_DEV", None)
    os.environ.pop("DATABASE_URL", None)
