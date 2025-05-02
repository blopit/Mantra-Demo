"""
Database adapter factory.

This module provides a factory for creating the appropriate database adapter
based on the environment configuration.
"""

import os
import logging
from typing import Optional

from src.adapters.database import DatabaseAdapter
from src.adapters.database.sqlite import SQLiteAdapter
from src.adapters.database.postgres import PostgresAdapter

logger = logging.getLogger(__name__)

class DatabaseAdapterFactory:
    """Factory for creating database adapters."""
    
    _instance: Optional[DatabaseAdapter] = None
    
    @classmethod
    async def get_adapter(cls) -> DatabaseAdapter:
        """Get the appropriate database adapter based on environment.
        
        Returns:
            DatabaseAdapter: The configured database adapter
            
        This method implements the singleton pattern to ensure only one
        database adapter instance exists throughout the application.
        """
        if cls._instance is None:
            environment = os.getenv("ENVIRONMENT", "development").lower()
            
            if environment == "development":
                # Use SQLite for development
                database_path = os.getenv("SQLITE_PATH", "sqlite.db")
                database_url = f"sqlite+aiosqlite:///{database_path}"
                cls._instance = SQLiteAdapter(database_url)
                logger.info("Using SQLite adapter for development")
            else:
                # Use PostgreSQL for production/staging
                database_url = os.getenv("DATABASE_URL")
                if not database_url:
                    raise ValueError("DATABASE_URL environment variable is required for non-development environments")
                cls._instance = PostgresAdapter(database_url)
                logger.info("Using PostgreSQL adapter for production/staging")
            
            # Initialize the adapter
            await cls._instance.init()
        
        return cls._instance
    
    @classmethod
    async def close_adapter(cls) -> None:
        """Close the current database adapter if it exists."""
        if cls._instance:
            await cls._instance.close()
            cls._instance = None
            logger.info("Closed database adapter") 