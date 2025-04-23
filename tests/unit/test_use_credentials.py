"""
Unit tests for the use_credentials example script.
"""

import sys
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

# Add the project root directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import the example script
from src.examples.use_credentials import main


class TestUseCredentials:
    """Tests for the use_credentials example script."""

    @patch("src.examples.use_credentials.get_user_info_from_credentials")
    @patch("src.examples.use_credentials.get_credentials_object")
    @patch("src.examples.use_credentials.build")
    def test_main_success(self, mock_build, mock_get_credentials, mock_get_user_info):
        """Test successful execution of the main function."""
        # Mock user info
        mock_get_user_info.return_value = {
            "email": "test@example.com",
            "name": "Test User"
        }
        
        # Mock credentials
        mock_credentials = MagicMock()
        mock_get_credentials.return_value = mock_credentials
        
        # Mock Gmail service
        mock_service = MagicMock()
        mock_profile = {"emailAddress": "test@example.com"}
        mock_messages = {"messages": [{"id": "msg1"}, {"id": "msg2"}]}
        mock_service.users().getProfile().execute.return_value = mock_profile
        mock_service.users().messages().list().execute.return_value = mock_messages
        mock_build.return_value = mock_service
        
        # Call the main function
        main()
        
        # Verify function calls
        mock_get_user_info.assert_called_once()
        mock_get_credentials.assert_called_once()
        mock_build.assert_called_once_with('gmail', 'v1', credentials=mock_credentials)
        mock_service.users().getProfile.assert_called_once()
        mock_service.users().messages().list.assert_called_once()

    @patch("src.examples.use_credentials.get_user_info_from_credentials")
    @patch("src.examples.use_credentials.get_credentials_object")
    @patch("src.examples.use_credentials.logger")
    def test_main_no_credentials(self, mock_logger, mock_get_credentials, mock_get_user_info):
        """Test main function when no credentials are found."""
        # Mock no user info
        mock_get_user_info.return_value = None
        
        # Mock no credentials
        mock_get_credentials.return_value = None
        
        # Call the main function
        main()
        
        # Verify function calls
        mock_get_user_info.assert_called_once()
        mock_get_credentials.assert_called_once()
        mock_logger.warning.assert_called_with("No user info found")
        mock_logger.error.assert_called_with("No credentials found in DATABASE_URL")

    @patch("src.examples.use_credentials.get_user_info_from_credentials")
    @patch("src.examples.use_credentials.get_credentials_object")
    @patch("src.examples.use_credentials.build")
    @patch("src.examples.use_credentials.logger")
    def test_main_api_error(self, mock_logger, mock_build, mock_get_credentials, mock_get_user_info):
        """Test main function when API call fails."""
        # Mock user info
        mock_get_user_info.return_value = {
            "email": "test@example.com",
            "name": "Test User"
        }
        
        # Mock credentials
        mock_credentials = MagicMock()
        mock_get_credentials.return_value = mock_credentials
        
        # Mock Gmail service with error
        mock_service = MagicMock()
        mock_service.users().getProfile().execute.side_effect = Exception("API error")
        mock_build.return_value = mock_service
        
        # Call the main function
        main()
        
        # Verify function calls
        mock_get_user_info.assert_called_once()
        mock_get_credentials.assert_called_once()
        mock_build.assert_called_once_with('gmail', 'v1', credentials=mock_credentials)
        mock_service.users().getProfile.assert_called_once()
        mock_logger.error.assert_called_with("Error using credentials: API error")
