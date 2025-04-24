"""
Google OAuth2 authentication service
"""
import os
import logging
from typing import Optional, Dict, Tuple
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

class GoogleAuthService:
    """Service for handling Google OAuth2 authentication"""
    
    def __init__(self):
        """Initialize the Google Auth Service"""
        self.client_id = os.getenv("GOOGLE_CLIENT_ID")
        self.client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        
        # Validate credentials
        if not self.client_id or not self.client_secret:
            logger.error("Google OAuth credentials not found in environment")
            raise ValueError("Google OAuth credentials not properly configured")
            
        self.scopes = [
            'openid',
            'https://www.googleapis.com/auth/userinfo.email',
            'https://www.googleapis.com/auth/userinfo.profile',
            'https://www.googleapis.com/auth/gmail.readonly',
            'https://www.googleapis.com/auth/calendar.readonly',
            'https://www.googleapis.com/auth/tasks.readonly'
        ]
        
    def get_authorization_url(self, redirect_url: str = None, user_id: str = None) -> str:
        """
        Get the Google OAuth2 authorization URL
        
        Args:
            redirect_url: URL to redirect to after authentication
            user_id: ID of the user requesting authorization
            
        Returns:
            str: Authorization URL
            
        Raises:
            ValueError: If redirect_url is invalid or credentials are missing
        """
        if not redirect_url:
            logger.error("No redirect URL provided")
            raise ValueError("redirect_url is required")
            
        try:
            logger.info(f"Generating auth URL with redirect to: {redirect_url}")
            
            # Create the flow using the client secrets
            flow = Flow.from_client_config(
                {
                    "web": {
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "redirect_uris": [redirect_url]
                    }
                },
                scopes=self.scopes,
                redirect_uri=redirect_url
            )
            
            # Generate the authorization URL with state containing user ID
            auth_url, _ = flow.authorization_url(
                access_type='offline',  # Enable offline access (needed for refresh token)
                include_granted_scopes='true',  # Include previously granted scopes
                prompt='consent',  # Force consent screen to get refresh token
                state=user_id  # Pass user ID as state
            )
            
            logger.info(f"Successfully generated authorization URL for user {user_id}")
            return auth_url
            
        except Exception as e:
            logger.error(f"Failed to generate authorization URL: {str(e)}")
            raise ValueError(f"Failed to generate authorization URL: {str(e)}")
    
    async def handle_callback(self, code: str, redirect_uri: str = None) -> Tuple[Dict, Credentials]:
        """
        Handle the OAuth2 callback and get user info
        
        Args:
            code: Authorization code from Google
            redirect_uri: The redirect URI used in the initial request
            
        Returns:
            Tuple[Dict, Credentials]: User information from Google and OAuth credentials
            
        Raises:
            ValueError: If code is invalid or credentials are missing
        """
        if not code:
            logger.error("No authorization code provided")
            raise ValueError("Authorization code is required")
            
        try:
            logger.info("Processing OAuth callback")
            
            # Create the flow using the client secrets
            flow = Flow.from_client_config(
                {
                    "web": {
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "redirect_uris": [redirect_uri] if redirect_uri else ["http://localhost:8000/api/google/callback"]
                    }
                },
                scopes=self.scopes,
                redirect_uri=redirect_uri or "http://localhost:8000/api/google/callback"
            )
            
            # Exchange the authorization code for credentials
            await flow.fetch_token(code=code)
            credentials = flow.credentials
            
            # Build the OAuth2 service
            service = build('oauth2', 'v2', credentials=credentials)
            
            # Get user info
            user_info = await service.userinfo().get().execute()
            logger.info(f"Successfully retrieved user info for: {user_info.get('email')}")
            
            return user_info, credentials
            
        except Exception as e:
            logger.error(f"Failed to handle callback: {str(e)}")
            raise ValueError(f"Failed to handle callback: {str(e)}")
            
    def refresh_token(self, refresh_token: str) -> Credentials:
        """
        Refresh the access token using a refresh token
        
        Args:
            refresh_token: The refresh token to use
            
        Returns:
            Credentials: New Google OAuth2 credentials
            
        Raises:
            ValueError: If refresh token is invalid or credentials are missing
        """
        if not refresh_token:
            logger.error("No refresh token provided")
            raise ValueError("Refresh token is required")
            
        try:
            logger.info("Attempting to refresh access token")
            
            credentials = Credentials(
                None,
                refresh_token=refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=self.client_id,
                client_secret=self.client_secret
            )
            
            # Refresh the credentials
            credentials.refresh(Request())
            logger.info("Successfully refreshed access token")
            
            return credentials
            
        except Exception as e:
            logger.error(f"Failed to refresh token: {str(e)}")
            raise ValueError(f"Failed to refresh token: {str(e)}") 
