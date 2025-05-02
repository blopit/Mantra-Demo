"""
PostgreSQL/Supabase database adapter implementation.

This module provides a PostgreSQL-specific implementation of the DatabaseAdapter
interface, optimized for production environments with Supabase support.
"""

import os
import logging
from typing import Any, Dict, List, Optional, Type, TypeVar
from sqlalchemy import create_engine, select, text, func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import QueuePool
from sqlalchemy.sql import Select

from src.adapters.database import DatabaseAdapter
from src.models.base import Base

logger = logging.getLogger(__name__)
T = TypeVar('T')

class PostgresAdapter(DatabaseAdapter):
    """PostgreSQL/Supabase adapter implementation."""
    
    def __init__(self, database_url: str):
        """Initialize the PostgreSQL adapter.
        
        Args:
            database_url: The database URL (PostgreSQL or Supabase)
        """
        self.database_url = database_url
        self.engine = None
        self.session_factory = None
    
    async def init(self) -> None:
        """Initialize the PostgreSQL database connection."""
        try:
            # Get environment variables for configuration
            pool_size = int(os.getenv("POOL_SIZE", "5"))
            max_overflow = int(os.getenv("MAX_OVERFLOW", "10"))
            pool_timeout = int(os.getenv("POOL_TIMEOUT", "30"))
            pool_recycle = int(os.getenv("POOL_RECYCLE", "1800"))  # 30 minutes
            
            # Create engine with PostgreSQL-specific optimizations
            self.engine = create_async_engine(
                self.database_url,
                poolclass=QueuePool,
                pool_size=pool_size,
                max_overflow=max_overflow,
                pool_timeout=pool_timeout,
                pool_recycle=pool_recycle,
                pool_pre_ping=True,  # Verify connections before using them
                echo=os.getenv("DEBUG", "False").lower() == "true"
            )
            
            # Create session factory
            self.session_factory = async_sessionmaker(
                bind=self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
                future=True
            )
            
            # Create tables if not using migrations
            if os.getenv("USE_MIGRATIONS", "False").lower() != "true":
                async with self.engine.begin() as conn:
                    await conn.run_sync(Base.metadata.create_all)
            
            logger.info(f"Initialized PostgreSQL database at {self.database_url}")
        except Exception as e:
            logger.error(f"Error initializing PostgreSQL database: {str(e)}")
            raise
    
    async def close(self) -> None:
        """Close the PostgreSQL database connection."""
        if self.engine:
            await self.engine.dispose()
            logger.info("Closed PostgreSQL database connection")
    
    async def get_session(self) -> AsyncSession:
        """Get a PostgreSQL database session.
        
        Returns:
            AsyncSession: A new database session
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
        async with self.get_session() as session:
            result = await session.execute(query)
            return result.scalars().all()
    
    async def create(self, model: Type[T], data: Dict[str, Any]) -> T:
        """Create a new database record.
        
        Args:
            model: The model class
            data: The data to create
            
        Returns:
            The created record
        """
        async with self.get_session() as session:
            instance = model(**data)
            session.add(instance)
            await session.commit()
            await session.refresh(instance)
            return instance
    
    async def get(self, model: Type[T], id: Any) -> Optional[T]:
        """Get a record by ID.
        
        Args:
            model: The model class
            id: The record ID
            
        Returns:
            The record if found, None otherwise
        """
        async with self.get_session() as session:
            result = await session.execute(select(model).where(model.id == id))
            return result.scalar_one_or_none()
    
    async def update(self, model: Type[T], id: Any, data: Dict[str, Any]) -> Optional[T]:
        """Update a record by ID.
        
        Args:
            model: The model class
            id: The record ID
            data: The data to update
            
        Returns:
            The updated record if found, None otherwise
        """
        async with self.get_session() as session:
            instance = await self.get(model, id)
            if instance:
                for key, value in data.items():
                    setattr(instance, key, value)
                await session.commit()
                await session.refresh(instance)
            return instance
    
    async def delete(self, model: Type[T], id: Any) -> bool:
        """Delete a record by ID.
        
        Args:
            model: The model class
            id: The record ID
            
        Returns:
            True if deleted, False if not found
        """
        async with self.get_session() as session:
            instance = await self.get(model, id)
            if instance:
                await session.delete(instance)
                await session.commit()
                return True
            return False
    
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
        return await self.execute_query(query)
    
    async def count(self, model: Type[T], filters: Optional[Dict[str, Any]] = None) -> int:
        """Count records with optional filters.
        
        Args:
            model: The model class
            filters: Optional filters to apply
            
        Returns:
            Number of records
        """
        async with self.get_session() as session:
            query = select(model)
            if filters:
                conditions = [getattr(model, k) == v for k, v in filters.items()]
                query = query.where(*conditions)
            result = await session.execute(select(func.count()).select_from(query.subquery()))
            return result.scalar_one()
    
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