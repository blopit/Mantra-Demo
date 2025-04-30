from uuid import uuid4
from sqlalchemy import Column, String, Boolean, DateTime, Integer, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from src.models.base import Base
from src.models.custom_types import UUIDType

class Mantra(Base):
    """
    Model for storing mantra workflows in the application.
    
    This model represents mantra workflows that can be installed by users.
    It stores the original n8n workflow JSON along with metadata.
    
    Attributes:
        id (UUID): Primary key, automatically generated UUID
        name (str): Name of the mantra
        description (str): Description of what the mantra does
        workflow_json (JSON): The original n8n workflow JSON
        created_at (datetime): When the mantra was created
        updated_at (datetime): When the mantra was last updated
        is_active (bool): Whether the mantra is active and available for installation
        user_id (str): ID of the user who created the mantra
    
    Relationships:
        user: Many-to-one relationship with Users
        installations: One-to-many relationship with MantraInstallation
    """
    __tablename__ = "mantras"
    
    id = Column(UUIDType, primary_key=True, default=uuid4)
    name = Column(String, nullable=False)
    description = Column(String)
    workflow_json = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_active = Column(Boolean, default=True)
    user_id = Column(String, ForeignKey("users.id"))
    
    # Relationships
    user = relationship("Users", back_populates="mantras")
    installations = relationship("MantraInstallation", back_populates="mantra")
    
    def __repr__(self):
        return f"<Mantra {self.name}>"

class MantraInstallation(Base):
    """
    Model for tracking installed mantras per user.
    
    This model represents the installation of a mantra by a user.
    It tracks the installation status and user-specific configuration.
    
    Attributes:
        id (UUID): Primary key, automatically generated UUID
        mantra_id (UUID): Foreign key to Mantra table
        user_id (str): Foreign key to Users table
        installed_at (datetime): When the mantra was installed
        status (str): Current status (active, paused, error)
        config (JSON): User-specific configuration for the mantra
        n8n_workflow_id (Integer): ID of the activated workflow in n8n
    
    Relationships:
        mantra: Many-to-one relationship with Mantra
        user: Many-to-one relationship with Users
    """
    __tablename__ = "mantra_installations"
    
    id = Column(UUIDType, primary_key=True, default=uuid4)
    mantra_id = Column(UUIDType, ForeignKey("mantras.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    installed_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    status = Column(String, default="active")
    config = Column(JSON)
    n8n_workflow_id = Column(Integer)
    
    # Relationships
    mantra = relationship("Mantra", back_populates="installations")
    user = relationship("Users", back_populates="mantra_installations")
    
    def __repr__(self):
        return f"<MantraInstallation {self.id}>" 