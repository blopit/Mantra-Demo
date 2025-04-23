"""
Google authentication manager for Ultimate Assistant.
Handles OAuth2 flow and authentication with Google services.
"""

import os
import logging
from typing import Dict, Any, Optional, List
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
import requests
import json
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timezone
import uuid

from .credentials import GoogleCredentialsManager
from src.utils.database import SessionLocal
from src.models.google_integration import GoogleIntegration
from src.utils.logger import get_logger

logger = get_logger(__name__)

class GoogleAuthManager:
    """Manages Google authentication flow"""

    # Default OAuth scopes
    DEFAULT_SCOPES = [
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/userinfo.email',
        'https://www.googleapis.com/auth/userinfo.profile'
    ]

    def __init__(self, db: Session):
        self.db = db
        self.credentials_manager = GoogleCredentialsManager()
        self.scopes = self.DEFAULT_SCOPES

    def get_authorization_url(self, redirect_uri: str, state: Optional[str] = None) -> str:
        """Get the URL for Google OAuth authorization"""
        if not self.credentials_manager.client_id or not self.credentials_manager.client_secret:
            raise ValueError("Missing client ID or client secret")

        # Create the flow using the client secrets
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": self.credentials_manager.client_id,
                    "client_secret": self.credentials_manager.client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [redirect_uri]
                }
            },
            scopes=self.scopes
        )

        # Set the redirect URI
        flow.redirect_uri = redirect_uri

        # Generate the authorization URL
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent',
            state=state
        )

        return auth_url

    def exchange_code(self, code: str, redirect_uri: str) -> Optional[Dict[str, Any]]:
        """Exchange an authorization code for credentials"""
        return self.credentials_manager.exchange_code(code, redirect_uri)

    def build_credentials(self, credentials_dict: Dict[str, Any]) -> Optional[Credentials]:
        """Build Google Credentials object from dictionary"""
        if not credentials_dict or "access_token" not in credentials_dict:
            return None

        try:
            credentials = Credentials(
                token=credentials_dict.get("access_token"),
                refresh_token=credentials_dict.get("refresh_token"),
                token_uri=credentials_dict.get("token_uri", "https://oauth2.googleapis.com/token"),
                client_id=credentials_dict.get("client_id", self.credentials_manager.client_id),
                client_secret=credentials_dict.get("client_secret", self.credentials_manager.client_secret),
                scopes=credentials_dict.get("scopes", self.scopes)
            )
            return credentials
        except Exception as e:
            logger.error(f"Error building credentials: {e}")
            return None

    def validate_and_refresh(self, credentials_dict: Dict[str, Any]) -> bool:
        """Validate credentials and refresh if needed"""
        if not credentials_dict or "access_token" not in credentials_dict:
            logger.error("Invalid credentials dictionary")
            return False

        try:
            # Build credentials object
            credentials = self.build_credentials(credentials_dict)
            if not credentials:
                logger.error("Failed to build credentials")
                return False

            # Check if token is expired
            if not credentials.valid:
                logger.info("Token expired, attempting to refresh")
                if not credentials.refresh_token:
                    logger.error("No refresh token available")
                    return False

                # Try to refresh the token
                try:
                    credentials.refresh(None)  # None means use the default request

                    # Update the credentials dictionary with new token
                    credentials_dict["access_token"] = credentials.token
                    if credentials.expiry:
                        credentials_dict["expiry"] = int(credentials.expiry.timestamp())

                    logger.info("Successfully refreshed token")
                    return True

                except Exception as e:
                    logger.error(f"Failed to refresh token: {e}")
                    return False

            return True

        except Exception as e:
            logger.error(f"Error validating credentials: {e}")
            return False

    def get_user_info(self, credentials_dict: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get user information from Google"""
        return self.credentials_manager.get_user_info(credentials_dict)

    def set_scopes(self, scopes: List[str]) -> None:
        """Set the OAuth scopes to request"""
        self.scopes = scopes

    async def get_credentials(self, user_id: uuid.UUID) -> Optional[Dict]:
        """Get stored Google OAuth credentials for a user."""
        try:
            integration = self.db.query(GoogleIntegration).filter(
                GoogleIntegration.user_id == user_id,
                GoogleIntegration.status == 'active'
            ).first()

            if not integration or not integration.access_token:
                return None

            return {
                'token': integration.access_token,
                'refresh_token': integration.refresh_token,
                'token_uri': 'https://oauth2.googleapis.com/token',
                'scopes': integration.scopes.split(','),
                'expiry': integration.token_expiry.isoformat() if integration.token_expiry else None
            }
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving Google credentials: {str(e)}")
            return None

    async def save_credentials(self, user_id: uuid.UUID, credentials: Dict) -> bool:
        """Save or update Google OAuth credentials for a user."""
        try:
            integration = self.db.query(GoogleIntegration).filter(
                GoogleIntegration.user_id == user_id,
                GoogleIntegration.status == 'active'
            ).first()

            if integration:
                # Update existing integration
                integration.access_token = credentials.get('token')
                integration.refresh_token = credentials.get('refresh_token', integration.refresh_token)
                integration.scopes = ','.join(credentials.get('scopes', []))
                integration.token_expiry = datetime.fromisoformat(credentials['expiry']) if credentials.get('expiry') else None
                integration.updated_at = datetime.now(timezone.utc)
            else:
                # Create new integration
                integration = GoogleIntegration(
                    id=uuid.uuid4(),
                    user_id=user_id,
                    access_token=credentials.get('token'),
                    refresh_token=credentials.get('refresh_token'),
                    scopes=','.join(credentials.get('scopes', [])),
                    token_expiry=datetime.fromisoformat(credentials['expiry']) if credentials.get('expiry') else None,
                    status='active',
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )
                self.db.add(integration)

            self.db.commit()
            return True
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Error saving Google credentials: {str(e)}")
            return False

    async def clear_credentials(self, user_id: uuid.UUID) -> bool:
        """Clear Google OAuth credentials for a user."""
        try:
            integration = self.db.query(GoogleIntegration).filter(
                GoogleIntegration.user_id == user_id,
                GoogleIntegration.status == 'active'
            ).first()

            if integration:
                integration.status = 'disconnected'
                integration.access_token = None  # Clear tokens for security
                integration.refresh_token = None
                integration.updated_at = datetime.now(timezone.utc)
                self.db.commit()
                return True
            return False
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Error clearing Google credentials: {str(e)}")
            return False
