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
        id (int): Primary key
        user_id (str): Foreign key to Users table
        service_name (str): Name of the Google service (gmail, calendar, drive)
        is_active (bool): Whether the integration is currently active
        scopes (str): Comma-separated list of OAuth scopes granted
        settings (str): JSON string of service-specific settings
        created_at (datetime): Record creation timestamp
        updated_at (datetime): Record last update timestamp
    """
    __tablename__ = "google_integrations"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    service_name = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    scopes = Column(String)
    settings = Column(String)  # JSON string of service-specific settings
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("Users", back_populates="google_integrations")
    
    def __repr__(self):
        return f"<GoogleIntegration {self.service_name} for user {self.user_id}>"


