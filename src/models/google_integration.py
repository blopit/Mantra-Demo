from datetime import datetime
from uuid import uuid4
from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from src.models.base import Base
from src.models.custom_types import UUIDType

class GoogleIntegration(Base):
    """Model for storing Google OAuth credentials and integration status"""
    __tablename__ = "google_integrations"
    
    id = Column(UUIDType, primary_key=True, default=uuid4)
    user_id = Column(UUIDType, ForeignKey("users.id"), nullable=False)
    email = Column(String, nullable=False)
    access_token = Column(Text, nullable=True)  # Nullable for revoked/disconnected state
    refresh_token = Column(Text, nullable=True)  # Nullable for revoked/disconnected state
    scopes = Column(Text, nullable=True)  # Comma-separated list of scopes
    token_expiry = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(20), nullable=False, default="active")  # active, disconnected
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationship
    user = relationship("Users", back_populates="google_integration")

    def __repr__(self):
        return f"<GoogleIntegration(user_id={self.user_id}, email={self.email}, status={self.status})>"
    
    
