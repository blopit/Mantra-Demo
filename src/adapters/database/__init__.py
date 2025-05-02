"""
Database adapters for seamless switching between SQLite and PostgreSQL/Supabase.

This module provides a consistent interface for database operations regardless
of the underlying database engine (SQLite or PostgreSQL/Supabase).
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type, TypeVar
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

T = TypeVar('T')

class DatabaseAdapter(ABC):
    """Abstract base class for database adapters."""
    
    @abstractmethod
    async def init(self) -> None:
        """Initialize the database connection and create tables."""
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Close the database connection."""
        pass
    
    @abstractmethod
    async def get_session(self) -> AsyncSession:
        """Get a database session.
        
        Returns:
            AsyncSession: A new database session
        """
        pass
    
    @abstractmethod
    async def execute_query(self, query: Select) -> Any:
        """Execute a database query.
        
        Args:
            query: The query to execute
            
        Returns:
            The query results
        """
        pass
    
    @abstractmethod
    async def create(self, model: Type[T], data: Dict[str, Any]) -> T:
        """Create a new database record.
        
        Args:
            model: The model class
            data: The data to create
            
        Returns:
            The created record
        """
        pass
    
    @abstractmethod
    async def get(self, model: Type[T], id: Any) -> Optional[T]:
        """Get a record by ID.
        
        Args:
            model: The model class
            id: The record ID
            
        Returns:
            The record if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def update(self, model: Type[T], id: Any, data: Dict[str, Any]) -> Optional[T]:
        """Update a record by ID.
        
        Args:
            model: The model class
            id: The record ID
            data: The data to update
            
        Returns:
            The updated record if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def delete(self, model: Type[T], id: Any) -> bool:
        """Delete a record by ID.
        
        Args:
            model: The model class
            id: The record ID
            
        Returns:
            True if deleted, False if not found
        """
        pass
    
    @abstractmethod
    async def list(self, model: Type[T], filters: Optional[Dict[str, Any]] = None) -> List[T]:
        """List records with optional filters.
        
        Args:
            model: The model class
            filters: Optional filters to apply
            
        Returns:
            List of records
        """
        pass
    
    @abstractmethod
    async def count(self, model: Type[T], filters: Optional[Dict[str, Any]] = None) -> int:
        """Count records with optional filters.
        
        Args:
            model: The model class
            filters: Optional filters to apply
            
        Returns:
            Number of records
        """
        pass
    
    @abstractmethod
    async def exists(self, model: Type[T], filters: Dict[str, Any]) -> bool:
        """Check if records exist with the given filters.
        
        Args:
            model: The model class
            filters: Filters to apply
            
        Returns:
            True if records exist, False otherwise
        """
        pass 