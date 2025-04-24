from datetime import datetime
from uuid import uuid4
from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from src.models.base import Base
from src.models.custom_types import UUIDType

class GoogleIntegration(Base):
    """
    Model for storing Google OAuth credentials and integration status.

    This model stores the OAuth tokens and related information needed to
    interact with Google APIs on behalf of a user. It maintains the connection
    between a user in our system and their Google account.

    Attributes:
        id (UUID): Primary key, automatically generated UUID
        user_id (UUID): Foreign key to the Users table
        email (str): The Google account email address
        access_token (str): OAuth access token for API calls
        refresh_token (str): OAuth refresh token for getting new access tokens
        scopes (str): Comma-separated list of authorized OAuth scopes
        token_expiry (datetime): When the access token expires
        status (str): Integration status (active, disconnected)
        created_at (datetime): When the integration was created
        updated_at (datetime): When the integration was last updated

    Relationships:
        user: Many-to-one relationship with Users

    Security Note:
        This model stores sensitive OAuth tokens. In a production environment,
        these should be encrypted at rest and proper access controls should
        be implemented.
    """
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


