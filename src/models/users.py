from uuid import uuid4
from sqlalchemy import Column, String, DateTime, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from src.models.base import Base
from src.models.custom_types import UUIDType

class Users(Base):
    """
    Model for storing user data.
    """
    __tablename__ = "users"

    id = Column(UUIDType, primary_key=True, default=uuid4)
    email = Column(String, unique=True, nullable=False)
    name = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    google_integration = relationship("GoogleIntegration", back_populates="user", uselist=False)
    contacts = relationship("Contacts", back_populates="user")

    def __repr__(self):
        return f"<User {self.email}>"
    
