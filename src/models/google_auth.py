"""
Model for storing Google OAuth authentication data.
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from src.models.base import Base

class GoogleAuth(Base):
    """
    Model for storing Google OAuth authentication data.
    
    This model maintains Google OAuth tokens and related user information.
    Note: In production, sensitive fields should be encrypted at rest.
    
    Attributes:
        id (int): Primary key
        user_id (str): Foreign key to Users table
        email (str): Google account email
        access_token (str): OAuth access token
        refresh_token (str): OAuth refresh token
        token_expiry (datetime): Access token expiration timestamp
        created_at (datetime): Record creation timestamp
        updated_at (datetime): Record last update timestamp
    """
    __tablename__ = "google_auth"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), unique=True, nullable=False)
    email = Column(String, nullable=False)
    access_token = Column(Text)
    refresh_token = Column(Text)
    token_expiry = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships - using string reference to avoid circular imports
    user = relationship("Users", back_populates="google_auth")
    
    def __repr__(self):
        return f"<GoogleAuth user_id={self.user_id} email={self.email}>" 