"""
Google authentication manager for Mantra Demo application.

This module handles the OAuth2 flow and authentication with Google services,
providing a unified interface for:
- Generating authorization URLs
- Exchanging authorization codes for tokens
- Validating and refreshing tokens
- Storing and retrieving credentials
- Getting user information from Google

The manager works with the database to persist credentials and integration status,
allowing for long-term access to Google services on behalf of users.

Security Note:
    This module handles sensitive OAuth tokens. In a production environment,
    additional security measures should be implemented, such as token encryption
    and more robust error handling.
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
    """
    Manages Google authentication flow and credential lifecycle.

    This class provides methods for initiating the OAuth flow, exchanging
    authorization codes for tokens, validating and refreshing tokens, and
    storing/retrieving credentials from the database.

    The manager works with a database session to persist credentials and
    maintain the state of Google integrations for users.

    Attributes:
        db (Session): SQLAlchemy database session
        credentials_manager (GoogleCredentialsManager): Helper for credential operations
        scopes (List[str]): OAuth scopes to request during authorization
    """

    # Default OAuth scopes
    DEFAULT_SCOPES = [
        'openid',
        'https://www.googleapis.com/auth/userinfo.email',
        'https://www.googleapis.com/auth/userinfo.profile'
    ]

    def __init__(self, db: Session):
        self.db = db
        self.credentials_manager = GoogleCredentialsManager()
        self.scopes = self.DEFAULT_SCOPES

    def get_authorization_url(self, redirect_uri: str, state: Optional[str] = None) -> str:
        """
        Get the URL for Google OAuth authorization.

        This method generates a URL that the user should be redirected to in order
        to authorize the application to access their Google data. The URL includes
        the requested scopes, redirect URI, and state parameter for security.

        Args:
            redirect_uri (str): The URI to redirect to after authorization
            state (Optional[str]): A random string to prevent CSRF attacks

        Returns:
            str: The authorization URL to redirect the user to

        Raises:
            ValueError: If client ID or client secret is missing
        """
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
        """
        Exchange an authorization code for credentials.

        After the user authorizes the application, Google redirects to the
        redirect_uri with an authorization code. This method exchanges that
        code for access and refresh tokens that can be used to make API calls.

        Args:
            code (str): The authorization code from Google
            redirect_uri (str): The redirect URI used in the authorization request

        Returns:
            Optional[Dict[str, Any]]: A dictionary containing the credentials,
                including access_token, refresh_token, token_uri, etc.,
                or None if the exchange fails
        """
        return self.credentials_manager.exchange_code(code, redirect_uri)

    def build_credentials(self, credentials_dict: Dict[str, Any]) -> Optional[Credentials]:
        """
        Build Google Credentials object from a dictionary.

        This method converts a dictionary representation of credentials
        (typically stored in the database) into a Google Credentials object
        that can be used with Google API client libraries.

        Args:
            credentials_dict (Dict[str, Any]): Dictionary containing credential information
                Must include at least 'access_token'

        Returns:
            Optional[Credentials]: A Google Credentials object, or None if invalid
        """
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
        """
        Validate credentials and refresh them if needed.

        This method checks if the provided credentials are valid and not expired.
        If they are expired but have a refresh token, it attempts to refresh them.
        The credentials_dict is updated in-place if refreshed successfully.

        Args:
            credentials_dict (Dict[str, Any]): Dictionary containing credential information
                Must include 'access_token' and should include 'refresh_token' for refresh

        Returns:
            bool: True if credentials are valid or were refreshed successfully,
                False otherwise
        """
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
        """
        Get user information from Google.

        This method uses the provided credentials to fetch the user's profile
        information from Google's userinfo endpoint.

        Args:
            credentials_dict (Dict[str, Any]): Dictionary containing credential information
                Must include 'access_token'

        Returns:
            Optional[Dict[str, Any]]: User information including email, name, etc.,
                or None if the request fails
        """
        return self.credentials_manager.get_user_info(credentials_dict)

    def set_scopes(self, scopes: List[str]) -> None:
        """
        Set the OAuth scopes to request during authorization.

        This method allows customizing which Google API permissions will be
        requested when generating an authorization URL.

        Args:
            scopes (List[str]): List of OAuth scope strings
                Example: ['https://www.googleapis.com/auth/gmail.readonly']
        """
        self.scopes = scopes

    async def get_credentials(self, user_id: uuid.UUID) -> Optional[Dict]:
        """
        Get stored Google OAuth credentials for a user.

        This method retrieves the stored credentials for a user from the database,
        formatted as a dictionary that can be used to create a Credentials object.

        Args:
            user_id (uuid.UUID): The ID of the user to get credentials for

        Returns:
            Optional[Dict]: A dictionary containing the credentials,
                or None if no active integration exists

        Raises:
            SQLAlchemyError: If there's a database error
        """
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
        """
        Save or update Google OAuth credentials for a user.

        This method stores the provided credentials in the database, either by
        updating an existing integration or creating a new one.

        Args:
            user_id (uuid.UUID): The ID of the user to save credentials for
            credentials (Dict): The credentials to save
                Should include 'token' (access token), 'refresh_token',
                'scopes', and optionally 'expiry'

        Returns:
            bool: True if saved successfully, False otherwise

        Raises:
            SQLAlchemyError: If there's a database error (will be caught and logged)
        """
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
        """
        Clear Google OAuth credentials for a user.

        This method marks a user's Google integration as disconnected and
        clears the stored tokens for security.

        Args:
            user_id (uuid.UUID): The ID of the user to clear credentials for

        Returns:
            bool: True if cleared successfully, False if no active integration exists

        Raises:
            SQLAlchemyError: If there's a database error (will be caught and logged)
        """
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
