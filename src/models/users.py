from uuid import uuid4
from sqlalchemy import Column, String, DateTime, Boolean, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from src.models.base import Base
from src.models.custom_types import UUIDType
from src.models.google_auth import GoogleAuth
from src.models.google_integration import GoogleIntegration

class Users(Base):
    """
    Model for user accounts in the system.
    
    This model stores core user information and maintains relationships
    with various integration models.
    
    Attributes:
        id (str): Primary key - stores large Google user IDs as strings
        email (str): User's email address
        name (str): User's full name
        is_active (bool): Whether user account is active
        created_at (datetime): Record creation timestamp
        updated_at (datetime): Record last update timestamp
        profile_picture (str): URL to user's profile picture
    """
    __tablename__ = "users"
    
    id = Column(String, primary_key=True)  # Changed to String to handle large Google user IDs
    email = Column(String, unique=True, nullable=False)
    name = Column(String)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    profile_picture = Column(String)
    
    # Relationships
    contacts = relationship("Contacts", back_populates="user", cascade="all, delete-orphan")
    google_auth = relationship("GoogleAuth", back_populates="user", uselist=False)
    google_integrations = relationship("GoogleIntegration", back_populates="user")
    mantra_installations = relationship("MantraInstallation", back_populates="user")
    mantras = relationship("Mantra", back_populates="user")
    
    def __repr__(self):
        return f"<User {self.email}>"

