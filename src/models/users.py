from uuid import uuid4
from sqlalchemy import Column, String, DateTime, Boolean, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from src.models.base import Base
from src.models.custom_types import UUIDType

class Users(Base):
    """
    Model for storing user data in the application.

    This model represents users in the system and stores their basic information.
    It serves as the central entity that other models relate to, such as
    GoogleIntegration and Contacts.

    Attributes:
        id (UUID): Primary key, automatically generated UUID
        email (str): User's email address, must be unique
        name (str): User's full name
        profile_picture (str): User's profile picture URL
        is_active (bool): Whether the user account is active
        created_at (datetime): When the user was created
        updated_at (datetime): When the user was last updated

    Relationships:
        google_integration: One-to-one relationship with GoogleIntegration
        contacts: One-to-many relationship with Contacts
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    name = Column(String)
    profile_picture = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    hashed_password = Column(String)

    # Relationships
    google_integration = relationship("GoogleIntegration", back_populates="user", uselist=False)
    contacts = relationship("Contacts", back_populates="user")
    google_auth = relationship("GoogleAuth", back_populates="user")

    def __repr__(self):
        return f"<User {self.email}>"

