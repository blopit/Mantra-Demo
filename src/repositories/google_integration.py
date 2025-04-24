"""
Repository for GoogleIntegration model operations.

This module provides database access methods for the GoogleIntegration model,
implementing the repository pattern to separate business logic from data access.
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
import logging

from src.repositories.base import BaseRepository
from src.models.google_integration import GoogleIntegration

logger = logging.getLogger(__name__)

class GoogleIntegrationRepository(BaseRepository[GoogleIntegration]):
    """
    Repository for GoogleIntegration database operations.
    
    This class extends the BaseRepository to provide specific query methods
    for the GoogleIntegration model.
    """
    
    def __init__(self, db: Session):
        """
        Initialize the repository with a database session.
        
        Args:
            db (Session): SQLAlchemy database session
        """
        super().__init__(db, GoogleIntegration)
    
    def get_by_user_id(self, user_id: str) -> Optional[GoogleIntegration]:
        """
        Get a GoogleIntegration by user ID.
        
        Args:
            user_id (str): User ID to search for
            
        Returns:
            Optional[GoogleIntegration]: GoogleIntegration instance if found, None otherwise
        """
        return self.db.query(self.model).filter(self.model.user_id == user_id).first()
    
    def get_by_email(self, email: str) -> Optional[GoogleIntegration]:
        """
        Get a GoogleIntegration by email.
        
        Args:
            email (str): Email to search for
            
        Returns:
            Optional[GoogleIntegration]: GoogleIntegration instance if found, None otherwise
        """
        return self.db.query(self.model).filter(self.model.email == email).first()
    
    def get_active_integrations(self, skip: int = 0, limit: int = 100) -> List[GoogleIntegration]:
        """
        Get all active GoogleIntegration records.
        
        Args:
            skip (int): Number of records to skip
            limit (int): Maximum number of records to return
            
        Returns:
            List[GoogleIntegration]: List of active GoogleIntegration instances
        """
        return self.db.query(self.model).filter(
            self.model.status == "active"
        ).offset(skip).limit(limit).all()
    
    def search(self, query: str, skip: int = 0, limit: int = 100) -> List[GoogleIntegration]:
        """
        Search for GoogleIntegration records.
        
        Args:
            query (str): Search query string
            skip (int): Number of records to skip
            limit (int): Maximum number of records to return
            
        Returns:
            List[GoogleIntegration]: List of matching GoogleIntegration instances
        """
        search_term = f"%{query}%"
        return self.db.query(self.model).filter(
            or_(
                self.model.email.ilike(search_term),
                self.model.status.ilike(search_term)
            )
        ).offset(skip).limit(limit).all()
    
    def update_token(self, integration_id: str, access_token: str, 
                    refresh_token: Optional[str] = None, 
                    token_expiry: Optional[Any] = None) -> Optional[GoogleIntegration]:
        """
        Update OAuth tokens for a GoogleIntegration.
        
        Args:
            integration_id (str): GoogleIntegration ID
            access_token (str): New access token
            refresh_token (Optional[str]): New refresh token (if available)
            token_expiry (Optional[Any]): New token expiry datetime
            
        Returns:
            Optional[GoogleIntegration]: Updated GoogleIntegration instance if found, None otherwise
        """
        integration = self.get_by_id(integration_id)
        if not integration:
            return None
        
        integration.access_token = access_token
        if refresh_token:
            integration.refresh_token = refresh_token
        if token_expiry:
            integration.token_expiry = token_expiry
        
        self.db.commit()
        self.db.refresh(integration)
        return integration
