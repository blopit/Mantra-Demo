"""
Base repository pattern implementation for database operations.

This module provides a generic repository pattern implementation that can be
extended by specific model repositories. It includes common CRUD operations
and query patterns to promote code reuse and consistent database access.
"""

from typing import List, Optional, Dict, Any, TypeVar, Generic, Type
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from sqlalchemy.sql import text
import logging

from src.models.base import Base

# Type variable for the model
T = TypeVar('T', bound=Base)

logger = logging.getLogger(__name__)

class BaseRepository(Generic[T]):
    """
    Generic repository for database operations.
    
    This class provides common CRUD operations for any SQLAlchemy model.
    It can be extended by specific model repositories to add custom queries.
    
    Attributes:
        db (Session): SQLAlchemy database session
        model (Type[T]): SQLAlchemy model class
    """
    
    def __init__(self, db: Session, model: Type[T]):
        """
        Initialize the repository with a database session and model class.
        
        Args:
            db (Session): SQLAlchemy database session
            model (Type[T]): SQLAlchemy model class
        """
        self.db = db
        self.model = model
    
    def get_all(self, skip: int = 0, limit: int = 100) -> List[T]:
        """
        Get all records with pagination.
        
        Args:
            skip (int): Number of records to skip
            limit (int): Maximum number of records to return
            
        Returns:
            List[T]: List of model instances
        """
        return self.db.query(self.model).offset(skip).limit(limit).all()
    
    def get_by_id(self, id: Any) -> Optional[T]:
        """
        Get a record by ID.
        
        Args:
            id (Any): Primary key value
            
        Returns:
            Optional[T]: Model instance if found, None otherwise
        """
        return self.db.query(self.model).filter(self.model.id == id).first()
    
    def create(self, data: Dict[str, Any]) -> T:
        """
        Create a new record.
        
        Args:
            data (Dict[str, Any]): Dictionary of field values
            
        Returns:
            T: Created model instance
        """
        db_item = self.model(**data)
        self.db.add(db_item)
        self.db.commit()
        self.db.refresh(db_item)
        return db_item
    
    def update(self, id: Any, data: Dict[str, Any]) -> Optional[T]:
        """
        Update a record by ID.
        
        Args:
            id (Any): Primary key value
            data (Dict[str, Any]): Dictionary of field values to update
            
        Returns:
            Optional[T]: Updated model instance if found, None otherwise
        """
        db_item = self.get_by_id(id)
        if db_item:
            for key, value in data.items():
                if hasattr(db_item, key):
                    setattr(db_item, key, value)
            self.db.commit()
            self.db.refresh(db_item)
        return db_item
    
    def delete(self, id: Any) -> bool:
        """
        Delete a record by ID.
        
        Args:
            id (Any): Primary key value
            
        Returns:
            bool: True if deleted, False if not found
        """
        db_item = self.get_by_id(id)
        if db_item:
            self.db.delete(db_item)
            self.db.commit()
            return True
        return False
    
    def search(self, query: str, skip: int = 0, limit: int = 100) -> List[T]:
        """
        Search for records matching a query string.
        
        This is a basic implementation that should be overridden by
        specific repositories to provide more targeted search functionality.
        
        Args:
            query (str): Search query string
            skip (int): Number of records to skip
            limit (int): Maximum number of records to return
            
        Returns:
            List[T]: List of matching model instances
        """
        # This is a placeholder implementation
        # Specific repositories should override this with more targeted search
        return self.get_all(skip, limit)
