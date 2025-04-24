"""
Google provider module for Ultimate Assistant.

This module provides integration with Google services including:
- Gmail
- Calendar
- Authentication

Each service can be used independently or together.
"""

from typing import Dict, Any, Optional, List
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build as google_build

# Import auth components
from .auth import GoogleAuthManager, GoogleCredentialsManager

# Import Gmail components
from .gmail import GmailAdapter, GmailService

# Import Calendar components
from .calendar import CalendarAdapter, CalendarService

__all__ = [
    'GoogleAuthManager',
    'GoogleCredentialsManager',
    'GmailAdapter',
    'GmailService',
    'CalendarAdapter',
    'CalendarService',
    'build'
]

def build(service_name: str, version: str, credentials: Optional[Credentials] = None, **kwargs) -> Any:
    """Build a Google API service object."""
    return google_build(service_name, version, credentials=credentials, **kwargs)
