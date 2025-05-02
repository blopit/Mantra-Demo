"""
SQLite database adapter implementation.

This module provides a SQLite-specific implementation of the DatabaseAdapter
interface, optimized for development and testing environments.
"""

import os
import logging
from typing import Any, Dict, List, Optional, Type, TypeVar
from sqlalchemy import create_engine, select, text, func, event
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy.sql import Select

from src.adapters.database import DatabaseAdapter
from src.models.base import Base

logger = logging.getLogger(__name__)
T = TypeVar('T')

class SQLiteAdapter(DatabaseAdapter):
    """SQLite adapter implementation."""
    
    def __init__(self, database_url: str = None):
        """Initialize the SQLite adapter.
        
        Args:
            database_url: Optional database URL. If not provided, uses in-memory SQLite.
        """
        self.database_url = database_url or "sqlite+aiosqlite://"
        self.engine = None
        self.session_factory = None
    
    async def init(self) -> None:
        """Initialize the SQLite database connection and create tables."""
        try:
            # Create engine with SQLite-specific optimizations
            self.engine = create_async_engine(
                self.database_url,
                connect_args={"check_same_thread": False},
                poolclass=NullPool,  # Use NullPool for SQLite
                echo=os.getenv("DEBUG", "False").lower() == "true"
            )
            
            # Enable foreign key support for SQLite
            @event.listens_for(self.engine.sync_engine, "connect", insert=True)
            def _enable_foreign_keys(dbapi_connection, connection_record):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()

            # Create session factory
            self.session_factory = async_sessionmaker(
                bind=self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
                future=True
            )
            
            # Create tables
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            
            logger.info(f"Initialized SQLite database at {self.database_url}")
        except Exception as e:
            logger.error(f"Error initializing SQLite database: {str(e)}")
            raise
    
    async def close(self) -> None:
        """Close the SQLite database connection."""
        if self.engine:
            await self.engine.dispose()
            logger.info("Closed SQLite database connection")
    
    async def get_session(self) -> AsyncSession:
        """Get a SQLite database session.
        
        Returns:
            AsyncSession: A session object
        """
        if not self.session_factory:
            raise RuntimeError("Database not initialized. Call init() first.")
        return self.session_factory()
    
    async def execute_query(self, query: Select) -> Any:
        """Execute a database query.
        
        Args:
            query: The query to execute
            
        Returns:
            The query results
        """
        session = await self.get_session()
        try:
            result = await session.execute(query)
            return result.scalars().all()
        finally:
            await session.close()
    
    async def create(self, model: Type[T], data: Dict[str, Any]) -> T:
        """Create a new database record.
        
        Args:
            model: The model class
            data: The data to create
            
        Returns:
            The created record
        """
        session = await self.get_session()
        try:
            instance = model(**data)
            session.add(instance)
            await session.commit()
            await session.refresh(instance)
            return instance
        finally:
            await session.close()
    
    async def get(self, model: Type[T], id: Any) -> Optional[T]:
        """Get a record by ID.
        
        Args:
            model: The model class
            id: The record ID
            
        Returns:
            The record if found, None otherwise
        """
        session = await self.get_session()
        try:
            result = await session.execute(select(model).where(model.id == id))
            return result.scalar_one_or_none()
        finally:
            await session.close()
    
    async def update(self, model: Type[T], id: Any, data: Dict[str, Any]) -> Optional[T]:
        """Update a record by ID.
        
        Args:
            model: The model class
            id: The record ID
            data: The data to update
            
        Returns:
            The updated record if found, None otherwise
        """
        session = await self.get_session()
        try:
            result = await session.execute(select(model).where(model.id == id))
            instance = result.scalar_one_or_none()
            if instance:
                for key, value in data.items():
                    setattr(instance, key, value)
                await session.commit()
                await session.refresh(instance)
                return instance
            return None
        finally:
            await session.close()
    
    async def delete(self, model: Type[T], id: Any) -> bool:
        """Delete a record by ID.
        
        Args:
            model: The model class
            id: The record ID
            
        Returns:
            True if deleted, False if not found
        """
        session = await self.get_session()
        try:
            result = await session.execute(select(model).where(model.id == id))
            instance = result.scalar_one_or_none()
            if instance:
                await session.delete(instance)
                await session.commit()
                return True
            return False
        finally:
            await session.close()
    
    async def list(self, model: Type[T], filters: Optional[Dict[str, Any]] = None) -> List[T]:
        """List records with optional filters.
        
        Args:
            model: The model class
            filters: Optional filters to apply
            
        Returns:
            List of records
        """
        query = select(model)
        if filters:
            conditions = [getattr(model, k) == v for k, v in filters.items()]
            query = query.where(*conditions)
        
        session = await self.get_session()
        try:
            result = await session.execute(query)
            return result.scalars().all()
        finally:
            await session.close()
    
    async def count(self, model: Type[T], filters: Optional[Dict[str, Any]] = None) -> int:
        """Count records with optional filters.
        
        Args:
            model: The model class
            filters: Optional filters to apply
            
        Returns:
            Number of records
        """
        session = await self.get_session()
        try:
            query = select(model)
            if filters:
                conditions = [getattr(model, k) == v for k, v in filters.items()]
                query = query.where(*conditions)
            result = await session.execute(select(func.count()).select_from(query.subquery()))
            return result.scalar_one()
        finally:
            await session.close()
    
    async def exists(self, model: Type[T], filters: Dict[str, Any]) -> bool:
        """Check if records exist with the given filters.
        
        Args:
            model: The model class
            filters: Filters to apply
            
        Returns:
            True if records exist, False otherwise
        """
        count = await self.count(model, filters)
        return count > 0 