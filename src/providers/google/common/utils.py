"""
Common utilities for Google provider modules.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

logger = logging.getLogger(__name__)

def build_credentials(credentials_dict: Dict[str, Any]) -> Optional[Credentials]:
    """
    Build Google Credentials object from dictionary
    
    Args:
        credentials_dict: Dictionary containing credential information
        
    Returns:
        Optional[Credentials]: Google Credentials object or None if invalid
    """
    if not credentials_dict or "access_token" not in credentials_dict:
        logger.error("Invalid credentials dictionary")
        return None
    
    try:
        credentials = Credentials(
            token=credentials_dict.get("access_token"),
            refresh_token=credentials_dict.get("refresh_token"),
            token_uri=credentials_dict.get("token_uri", "https://oauth2.googleapis.com/token"),
            client_id=credentials_dict.get("client_id"),
            client_secret=credentials_dict.get("client_secret"),
            scopes=credentials_dict.get("scopes")
        )
        return credentials
    except Exception as e:
        logger.error(f"Error building credentials: {e}")
        return None

def refresh_credentials(credentials: Credentials) -> bool:
    """
    Refresh Google credentials if expired
    
    Args:
        credentials: Google Credentials object
        
    Returns:
        bool: True if refresh successful or not needed, False otherwise
    """
    if not credentials:
        logger.error("No credentials provided")
        return False
    
    try:
        # Check if credentials are expired
        if credentials.expired:
            logger.info("Credentials expired, attempting refresh")
            if not credentials.refresh_token:
                logger.error("No refresh token available")
                return False
            
            # Try to refresh the token
            credentials.refresh(Request())
            logger.info("Successfully refreshed credentials")
        
        return True
    except Exception as e:
        logger.error(f"Error refreshing credentials: {e}")
        return False

def format_datetime(dt: datetime, format_str: str = '%Y-%m-%d %H:%M:%S') -> str:
    """
    Format datetime object to string
    
    Args:
        dt: Datetime object
        format_str: Format string
        
    Returns:
        str: Formatted datetime string
    """
    try:
        return dt.strftime(format_str)
    except Exception as e:
        logger.error(f"Error formatting datetime: {e}")
        return str(dt)

def parse_datetime(dt_str: str) -> Optional[datetime]:
    """
    Parse datetime string to datetime object
    
    Args:
        dt_str: Datetime string
        
    Returns:
        Optional[datetime]: Datetime object or None if invalid
    """
    try:
        # Try ISO format first
        return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
    except ValueError:
        try:
            # Try RFC 3339 format
            return datetime.strptime(dt_str, '%Y-%m-%dT%H:%M:%S.%fZ')
        except ValueError:
            try:
                # Try simple format
                return datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                logger.error(f"Could not parse datetime string: {dt_str}")
                return None
    except Exception as e:
        logger.error(f"Error parsing datetime: {e}")
        return None
