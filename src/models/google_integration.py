"""
Model for storing Google service integration details.
"""

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from src.models.base import Base

class GoogleIntegration(Base):
    """
    Model for storing Google service integration details.
    
    This model stores information about which Google services a user has
    integrated with their account (Gmail, Calendar, Drive, etc).
    
    Attributes:
        id (str): Primary key (UUID)
        user_id (str): Foreign key to Users table
        google_account_id (str): Google account ID (sub from OAuth)
        email (str): Google account email
        service_name (str): Name of the Google service (gmail, calendar, drive)
        is_active (bool): Whether the integration is currently active
        status (str): Integration status (active, inactive)
        access_token (str): OAuth access token
        refresh_token (str): OAuth refresh token
        expires_at (datetime): Token expiration timestamp
        scopes (str): Comma-separated list of OAuth scopes granted
        settings (str): JSON string of service-specific settings
        created_at (datetime): Record creation timestamp
        updated_at (datetime): Record last update timestamp
        disconnected_at (datetime): When the integration was disconnected
    """
    __tablename__ = "google_integrations"
    
    id = Column(String, primary_key=True)  # Changed to String for UUID
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    google_account_id = Column(String, nullable=False)
    email = Column(String, nullable=False)
    service_name = Column(String)
    is_active = Column(Boolean, default=True)
    status = Column(String, default="active")
    access_token = Column(String)
    refresh_token = Column(String)
    expires_at = Column(DateTime(timezone=True))
    scopes = Column(String)
    settings = Column(String)  # JSON string of service-specific settings
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    disconnected_at = Column(DateTime(timezone=True))
    
    # Relationships
    user = relationship("Users", back_populates="google_integrations")
    
    def __repr__(self):
        return f"<GoogleIntegration {self.service_name} for user {self.user_id}>"


