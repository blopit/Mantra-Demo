"""
Pydantic models for Google integration.
"""

from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime

class GoogleIntegrationBase(BaseModel):
    """Base model for Google integration"""
    access_token: str
    refresh_token: str
    token_uri: str = "https://oauth2.googleapis.com/token"
    client_id: str
    client_secret: str
    scopes: List[str]
    expires_at: Optional[datetime] = None

class GoogleIntegrationCreate(GoogleIntegrationBase):
    """Model for creating a new Google integration"""
    user_id: str

class GoogleIntegrationUpdate(BaseModel):
    """Model for updating an existing Google integration"""
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_uri: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    scopes: Optional[List[str]] = None
    expires_at: Optional[datetime] = None

class GoogleIntegrationResponse(GoogleIntegrationBase):
    """Model for Google integration response"""
    id: int
    user_id: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        """Pydantic config"""
        from_attributes = True 