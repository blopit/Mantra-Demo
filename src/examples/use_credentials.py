"""
Example of how to use the stored Google credentials.

This example demonstrates how to access Google credentials stored in DATABASE_URL
and use them to interact with Google APIs.
"""

import sys
import logging
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

# Import utility functions
from src.utils.google_credentials import get_credentials_object, get_user_info_from_credentials

# Import Google API libraries
try:
    from googleapiclient.discovery import build
    from dotenv import load_dotenv
    # Load environment variables
    load_dotenv()
except ImportError:
    logging.error("Required packages not installed. Run: pip install -r requirements.txt")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Example of using stored Google credentials"""
    # Get user info from credentials
    user_info = get_user_info_from_credentials()
    if user_info:
        logger.info(f"User info: {user_info}")
    else:
        logger.warning("No user info found")

    # Get credentials as a Google Credentials object
    credentials = get_credentials_object()
    if not credentials:
        logger.error("No credentials found in DATABASE_URL")
        return

    # Use credentials to access Google API
    try:
        # Create a service (e.g., Gmail)
        service = build('gmail', 'v1', credentials=credentials)

        # Get user profile
        profile = service.users().getProfile(userId='me').execute()
        logger.info(f"Gmail profile: {profile}")

        # Get email messages
        messages = service.users().messages().list(userId='me', maxResults=5).execute()
        logger.info(f"Found {len(messages.get('messages', []))} messages")

    except Exception as e:
        logger.error(f"Error using credentials: {str(e)}")

if __name__ == '__main__':
    main()
