"""
Configuration for service integrations.
"""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel


class IntegrationConfig(BaseModel):
    """Configuration for service integrations."""
    
    class Config:
        """Pydantic config"""
        arbitrary_types_allowed = True

    # Google Integration Settings
    google_client_id: Optional[str] = None
    google_client_secret: Optional[str] = None
    google_redirect_uri: Optional[str] = None
    google_auth_uri: str = "https://accounts.google.com/o/oauth2/auth"
    google_token_uri: str = "https://oauth2.googleapis.com/token"
    google_scopes: List[str] = [
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile",
        "openid"
    ]
    
    # Additional service settings can be added here
    settings: Dict[str, Any] = {}

    def get_google_config(self) -> Dict[str, Any]:
        """Get Google-specific configuration."""
        return {
            "client_id": self.google_client_id,
            "client_secret": self.google_client_secret,
            "redirect_uri": self.google_redirect_uri,
            "auth_uri": self.google_auth_uri,
            "token_uri": self.google_token_uri,
            "scopes": self.google_scopes
        }

    def update_settings(self, new_settings: Dict[str, Any]) -> None:
        """Update integration settings."""
        self.settings.update(new_settings)

    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a specific setting value."""
        return self.settings.get(key, default) 