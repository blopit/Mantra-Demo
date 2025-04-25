"""
Google credentials management for Ultimate Assistant.
Handles storage, validation, and refreshing of OAuth credentials.
"""

import os
import time
import logging
import requests
from typing import Dict, Any, Optional
import dotenv
import pathlib

logger = logging.getLogger(__name__)

class GoogleCredentialsManager:
    """Manages Google OAuth credentials"""
    TOKEN_URI = "https://oauth2.googleapis.com/token"
    USERINFO_URI = "https://www.googleapis.com/oauth2/v1/userinfo"
    
    def __init__(self):
        """Initialize the credentials manager"""
        # Ensure we're using the most up-to-date environment variables
        # Try to reload dotenv from absolute path to ensure we get the latest values
        env_path = pathlib.Path('.env').absolute()
        if env_path.exists():
            logger.info(f"Reloading environment variables from {env_path}")
            dotenv.load_dotenv(dotenv_path=env_path, override=True)
        
        # Get values from environment
        self.client_id = os.getenv("GOOGLE_CLIENT_ID", "")
        self.client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "")
        
        # Log what we're using (safely)
        client_id_prefix = self.client_id[:8] if len(self.client_id) > 10 else "***"
        client_secret_prefix = self.client_secret[:3] if len(self.client_secret) > 5 else "***"
        
        logger.info(f"GoogleCredentialsManager initialized with client_id prefix: {client_id_prefix}...")
        
        # Verify client ID format
        if self.client_id and not self.client_id.endswith(".apps.googleusercontent.com"):
            logger.warning("Client ID doesn't have expected format (should end with .apps.googleusercontent.com)")
    
    def setup(self, client_id: str, client_secret: str) -> bool:
        """Set up credentials with client ID and secret"""
        if not client_id or not client_secret:
            return False
            
        self.client_id = client_id
        self.client_secret = client_secret
        
        # Set environment variables for other components
        os.environ["GOOGLE_CLIENT_ID"] = client_id
        os.environ["GOOGLE_CLIENT_SECRET"] = client_secret
        
        return True
    
    def exchange_code(self, code: str, redirect_uri: str) -> Optional[Dict[str, Any]]:
        """Exchange an authorization code for tokens"""
        if not self.client_id or not self.client_secret:
            logger.error("Missing client ID or secret")
            return None
        
        try:
            token_data = {
                "code": code,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code"
            }
            
            response = requests.post(self.TOKEN_URI, data=token_data)
            if response.status_code != 200:
                logger.error(f"Error exchanging code for tokens: {response.text}")
                return None
            
            # Extract tokens from response
            token_info = response.json()
            
            # Structure credentials
            return {
                "access_token": token_info.get("access_token"),
                "refresh_token": token_info.get("refresh_token", ""),
                "token_uri": self.TOKEN_URI,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "scopes": ["openid",
                          "https://www.googleapis.com/auth/userinfo.email",
                          "https://www.googleapis.com/auth/userinfo.profile"],
                "expiry": int(time.time()) + token_info.get("expires_in", 3600)
            }
            
        except Exception as e:
            logger.error(f"Error in token exchange: {e}")
            return None
    
    def validate_credentials(self, credentials: Dict[str, Any]) -> bool:
        """Check if credentials are valid and refresh if needed"""
        if not credentials or "access_token" not in credentials:
            return False
        
        # Check if token is still valid
        try:
            response = requests.get(
                self.USERINFO_URI,
                headers={"Authorization": f"Bearer {credentials['access_token']}"}
            )
            if response.status_code == 200:
                return True
                
            # Token expired, try to refresh if we have a refresh token
            if "refresh_token" in credentials and credentials["refresh_token"]:
                refreshed_creds = self.refresh_token(credentials)
                if refreshed_creds:
                    # Update the passed credentials dict
                    credentials.update(refreshed_creds)
                    return True
        except Exception as e:
            logger.error(f"Error validating credentials: {e}")
        
        return False
    
    def refresh_token(self, credentials: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Refresh an expired access token"""
        if not credentials.get("refresh_token"):
            return None
            
        try:
            refresh_data = {
                "client_id": credentials.get("client_id", self.client_id),
                "client_secret": credentials.get("client_secret", self.client_secret),
                "refresh_token": credentials["refresh_token"],
                "grant_type": "refresh_token"
            }
            
            response = requests.post(self.TOKEN_URI, data=refresh_data)
            if response.status_code != 200:
                logger.error(f"Failed to refresh token: {response.text}")
                return None
                
            refresh_info = response.json()
            
            # Return updated credentials
            return {
                "access_token": refresh_info["access_token"],
                "expiry": int(time.time()) + refresh_info.get("expires_in", 3600)
            }
            
        except Exception as e:
            logger.error(f"Error refreshing token: {e}")
            return None
    
    def get_user_info(self, credentials: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get user info using valid credentials"""
        if not self.validate_credentials(credentials):
            return None
            
        try:
            response = requests.get(
                self.USERINFO_URI,
                headers={"Authorization": f"Bearer {credentials['access_token']}"}
            )
            
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.error(f"Error getting user info: {e}")
            
        return None

    def verify_client_credentials(self) -> bool:
        """
        Verify that client credentials are properly configured
        
        Returns:
            bool: True if credentials are properly configured
        """
        if not self.client_id:
            logger.error("GOOGLE_CLIENT_ID environment variable is not set or empty")
            return False
        
        if not self.client_secret:
            logger.error("GOOGLE_CLIENT_SECRET environment variable is not set or empty")
            return False
        
        # Log partial credentials for debugging (safely)
        client_id_prefix = self.client_id[:8] if len(self.client_id) > 10 else "***"
        client_secret_prefix = self.client_secret[:3] if len(self.client_secret) > 5 else "***"
        
        logger.info(f"Using Google client credentials - ID prefix: {client_id_prefix}..., Secret prefix: {client_secret_prefix}...")
        
        # Verify client ID format (typically ends with .apps.googleusercontent.com)
        if not self.client_id.endswith(".apps.googleusercontent.com"):
            logger.warning("Client ID doesn't have expected format (should end with .apps.googleusercontent.com)")
            # Not returning false here as this is just a warning
        
        return True
