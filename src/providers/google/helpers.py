"""
Helper functions for Google services.

This module provides helper functions for working with Google services,
including Gmail, Calendar, and other Google APIs.
"""

from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from google.oauth2.credentials import Credentials

from .gmail import GmailService
from .auth import GoogleCredentialsManager
from src.models.google_integration import GoogleIntegration

async def get_recent_emails(db, user_id, limit=20):
    """
    Get recent emails for a user
    
    This is a helper function used by the routes
    """
    # Find the user's Google integration
    google_integration = db.query(GoogleIntegration).filter(
        GoogleIntegration.user_id == user_id,
        GoogleIntegration.status == 'active'
    ).first()
    
    if not google_integration:
        raise ValueError("No active Google integration found")
    
    # Get email data
    gmail = GmailService()
    
    # Convert stored credentials to dict
    credentials_dict = {
        'token': google_integration.access_token,
        'refresh_token': google_integration.refresh_token,
        'token_uri': "https://oauth2.googleapis.com/token",
        'client_id': google_integration.client_id,
        'client_secret': google_integration.client_secret,
        'scopes': google_integration.scopes if isinstance(google_integration.scopes, list) else google_integration.scopes.split(',')
    }
    
    # Connect to Gmail
    if not await gmail.connect(credentials_dict):
        raise ValueError("Failed to connect to Gmail API")
    
    # Get messages
    return await gmail.get_messages(max_results=limit)

async def get_user_google_data(google_integration: GoogleIntegration) -> Dict[str, Any]:
    """
    Get comprehensive Google data for a user
    
    This is a helper function used by the routes
    """
    # Convert stored credentials to dict
    credentials_dict = {
        'token': google_integration.access_token,
        'refresh_token': google_integration.refresh_token,
        'token_uri': "https://oauth2.googleapis.com/token",
        'client_id': google_integration.client_id,
        'client_secret': google_integration.client_secret,
        'scopes': google_integration.scopes if isinstance(google_integration.scopes, list) else google_integration.scopes.split(',')
    }
    
    # Get email data
    gmail = GmailService()
    
    # Connect to Gmail
    if not await gmail.connect(credentials_dict):
        raise ValueError("Failed to connect to Gmail API")
    
    # Get messages
    emails = await gmail.get_messages(max_results=10)
    
    # For now, just return emails
    # TODO: Expand this to include calendar events, contacts, etc.
    return {
        'emails': emails
    }
