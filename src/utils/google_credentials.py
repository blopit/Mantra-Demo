"""
Utility functions for working with Google credentials.
Supports both database and DATABASE_URL storage methods.
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from google.oauth2.credentials import Credentials
from sqlalchemy.orm import Session

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Google API endpoints
GOOGLE_TOKEN_URI = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URI = "https://www.googleapis.com/oauth2/v3/userinfo"

def get_credentials_from_database_url() -> Optional[Dict[str, Any]]:
    """
    Get Google credentials from DATABASE_URL environment variable.

    Returns:
        Optional[Dict[str, Any]]: Credentials dictionary or None if not found
    """
    try:
        # Get DATABASE_URL from environment
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            logger.warning("DATABASE_URL environment variable not found")
            return None

        # Try to parse as JSON
        try:
            creds_dict = json.loads(database_url)
            return creds_dict
        except json.JSONDecodeError:
            # If not JSON, it's probably a real database URL
            logger.warning("DATABASE_URL is not in JSON format, might be a real database URL")
            return None
    except Exception as e:
        logger.error(f"Error getting Google credentials from DATABASE_URL: {str(e)}")
        return None

def get_credentials_from_database(db: Session, user_id: str) -> Optional[Dict[str, Any]]:
    """
    Get Google credentials from database.

    Args:
        db: Database session
        user_id: User ID

    Returns:
        Optional[Dict[str, Any]]: Credentials dictionary or None if not found
    """
    try:
        # Import here to avoid circular imports
        from src.models.google_integration import GoogleIntegration

        # Get active integration
        integration = db.query(GoogleIntegration).filter(
            GoogleIntegration.user_id == user_id,
            GoogleIntegration.status == "active"
        ).first()

        if not integration:
            logger.warning(f"No active Google integration found for user {user_id}")
            return None

        # Build credentials dictionary
        credentials = {
            "access_token": integration.access_token,
            "refresh_token": integration.refresh_token,
            "token_uri": GOOGLE_TOKEN_URI,
            "client_id": os.getenv("GOOGLE_CLIENT_ID", ""),
            "client_secret": os.getenv("GOOGLE_CLIENT_SECRET", ""),
            "scopes": integration.scopes.split(",") if isinstance(integration.scopes, str) else integration.scopes
        }

        # Add expiry if available
        if integration.token_expiry:
            credentials["expiry"] = integration.token_expiry.isoformat()

        return credentials
    except Exception as e:
        logger.error(f"Error getting Google credentials from database: {str(e)}")
        return None

def get_google_credentials() -> Optional[Dict[str, Any]]:
    """
    Get Google credentials from DATABASE_URL environment variable.
    Legacy function for backward compatibility.

    Returns:
        Optional[Dict[str, Any]]: Credentials dictionary or None if not found
    """
    return get_credentials_from_database_url()

def get_credentials(db: Optional[Session] = None, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Get Google credentials from either database or DATABASE_URL.
    Tries DATABASE_URL first, then falls back to database if provided.

    Args:
        db: Optional database session
        user_id: Optional user ID

    Returns:
        Optional[Dict[str, Any]]: Credentials dictionary or None if not found
    """
    # Try DATABASE_URL first
    credentials = get_credentials_from_database_url()
    if credentials:
        return credentials

    # Fall back to database if provided
    if db and user_id:
        return get_credentials_from_database(db, user_id)

    return None

def get_google_credentials_object() -> Optional[Credentials]:
    """
    Get Google credentials as a Credentials object.
    Legacy function for backward compatibility.

    Returns:
        Optional[Credentials]: Google Credentials object or None if not found
    """
    return get_credentials_object()

def get_credentials_object(db: Optional[Session] = None, user_id: Optional[str] = None) -> Optional[Credentials]:
    """
    Get Google credentials as a Credentials object.

    Args:
        db: Optional database session
        user_id: Optional user ID

    Returns:
        Optional[Credentials]: Google Credentials object or None if not found
    """
    creds_dict = get_credentials(db, user_id)
    if not creds_dict:
        return None

    try:
        # Parse expiry if it exists
        expiry = None
        if creds_dict.get('expiry'):
            try:
                expiry = datetime.fromisoformat(creds_dict['expiry'].replace("Z", "+00:00"))
            except (ValueError, TypeError):
                logger.warning(f"Could not parse expiry: {creds_dict['expiry']}")

        # Create Credentials object
        credentials = Credentials(
            token=creds_dict.get('access_token'),
            refresh_token=creds_dict.get('refresh_token'),
            token_uri=creds_dict.get('token_uri', GOOGLE_TOKEN_URI),
            client_id=creds_dict.get('client_id', os.getenv('GOOGLE_CLIENT_ID')),
            client_secret=creds_dict.get('client_secret', os.getenv('GOOGLE_CLIENT_SECRET')),
            scopes=creds_dict.get('scopes', []),
            expiry=expiry
        )

        return credentials
    except Exception as e:
        logger.error(f"Error creating Credentials object: {str(e)}")
        return None

def get_user_info() -> Optional[Dict[str, Any]]:
    """
    Get user info from stored Google credentials.
    Legacy function for backward compatibility.

    Returns:
        Optional[Dict[str, Any]]: User info dictionary or None if not found
    """
    return get_user_info_from_credentials()

def get_user_info_from_credentials(credentials_dict: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """
    Get user info from stored Google credentials.

    Args:
        credentials_dict: Optional credentials dictionary. If not provided, will try to get from DATABASE_URL.

    Returns:
        Optional[Dict[str, Any]]: User info dictionary or None if not found
    """
    if not credentials_dict:
        credentials_dict = get_credentials_from_database_url()

    if not credentials_dict:
        return None

    # Check if user_info is directly in the credentials
    if 'user_info' in credentials_dict:
        return credentials_dict['user_info']

    # Otherwise, try to fetch from Google API
    try:
        import requests

        response = requests.get(
            GOOGLE_USERINFO_URI,
            headers={"Authorization": f"Bearer {credentials_dict.get('access_token')}"}
        )

        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Error getting user info: {response.status_code} {response.text}")
            return None
    except Exception as e:
        logger.error(f"Error getting user info: {str(e)}")
        return None

def store_credentials_in_database_url(credentials_dict: Dict[str, Any], user_info: Dict[str, Any]) -> bool:
    """
    Store Google credentials in DATABASE_URL environment variable.

    Args:
        credentials_dict: Credentials dictionary
        user_info: User info dictionary

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Create credentials dictionary
        creds_dict = {
            "access_token": credentials_dict.get("access_token"),
            "refresh_token": credentials_dict.get("refresh_token"),
            "token_uri": credentials_dict.get("token_uri", GOOGLE_TOKEN_URI),
            "client_id": credentials_dict.get("client_id", os.getenv("GOOGLE_CLIENT_ID")),
            "client_secret": credentials_dict.get("client_secret", os.getenv("GOOGLE_CLIENT_SECRET")),
            "scopes": credentials_dict.get("scopes", []),
            "expiry": credentials_dict.get("expiry"),
            "user_info": {
                "email": user_info.get("email"),
                "name": user_info.get("name"),
                "picture": user_info.get("picture"),
                "id": user_info.get("sub")
            }
        }

        # Convert to JSON string
        creds_json = json.dumps(creds_dict)

        # Update .env file with new DATABASE_URL
        update_env_file("DATABASE_URL", creds_json)

        # Also update environment variable in current process
        os.environ["DATABASE_URL"] = creds_json

        return True
    except Exception as e:
        logger.error(f"Error storing credentials in DATABASE_URL: {str(e)}")
        return False

def clear_credentials_from_database_url() -> bool:
    """
    Clear Google credentials from DATABASE_URL environment variable.

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Check if DATABASE_URL contains credentials
        database_url = os.getenv("DATABASE_URL", "")
        try:
            json.loads(database_url)
            # If we can parse it as JSON, it's credentials
            update_env_file("DATABASE_URL", "")
            os.environ["DATABASE_URL"] = ""
        except json.JSONDecodeError:
            # Not JSON, probably a real database URL
            pass

        return True
    except Exception as e:
        logger.error(f"Error clearing credentials from DATABASE_URL: {str(e)}")
        return False

def update_env_file(key: str, value: str) -> bool:
    """
    Update a key in the .env file.

    Args:
        key: Environment variable key
        value: Environment variable value

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Read current .env file
        env_path = ".env"
        lines = []
        key_exists = False

        if os.path.exists(env_path):
            with open(env_path, "r") as file:
                lines = file.readlines()

        # Update or add the key
        new_lines = []
        for line in lines:
            if line.strip() and not line.startswith("#"):
                if line.split("=")[0].strip() == key:
                    new_lines.append(f"{key}='{value}'\n")
                    key_exists = True
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)

        if not key_exists:
            new_lines.append(f"{key}='{value}'\n")

        # Write back to .env file
        with open(env_path, "w") as file:
            file.writelines(new_lines)

        return True
    except Exception as e:
        logger.error(f"Error updating .env file: {str(e)}")
        return False
