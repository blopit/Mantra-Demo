"""
Unit tests for Google credentials utility functions.
"""

import os
import json
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

from src.utils.google_credentials import (
    get_credentials_from_database_url,
    get_user_info_from_credentials,
    store_credentials_in_database_url,
    clear_credentials_from_database_url,
    update_env_file
)


class TestGetCredentialsFromDatabaseUrl:
    """Tests for get_credentials_from_database_url function."""

    def test_no_database_url(self, mock_env_empty):
        """Test when DATABASE_URL is not set."""
        result = get_credentials_from_database_url()
        assert result is None

    def test_valid_database_url(self, mock_env_with_database_url):
        """Test when DATABASE_URL contains valid credentials."""
        expected = mock_env_with_database_url
        result = get_credentials_from_database_url()
        assert result == expected

    def test_invalid_database_url(self, mock_env_empty):
        """Test when DATABASE_URL is not valid JSON."""
        os.environ["DATABASE_URL"] = "not-valid-json"
        result = get_credentials_from_database_url()
        assert result is None


class TestGetUserInfoFromCredentials:
    """Tests for get_user_info_from_credentials function."""

    def test_no_credentials(self, mock_env_empty):
        """Test when no credentials are provided."""
        result = get_user_info_from_credentials()
        assert result is None

    def test_credentials_with_user_info(self, mock_env_with_database_url):
        """Test when credentials contain user_info."""
        expected = mock_env_with_database_url["user_info"]
        result = get_user_info_from_credentials(mock_env_with_database_url)
        assert result == expected

    @patch("requests.get")
    def test_credentials_without_user_info(self, mock_get, mock_credentials):
        """Test when credentials don't contain user_info but API call succeeds."""
        # Mock response from Google API
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "email": "test@example.com",
            "name": "Test User"
        }
        mock_get.return_value = mock_response

        result = get_user_info_from_credentials(mock_credentials)
        assert result == {"email": "test@example.com", "name": "Test User"}
        mock_get.assert_called_once()

    @patch("requests.get")
    def test_api_error(self, mock_get, mock_credentials):
        """Test when API call fails."""
        # Mock error response
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_get.return_value = mock_response

        result = get_user_info_from_credentials(mock_credentials)
        assert result is None
        mock_get.assert_called_once()


class TestStoreCredentialsInDatabaseUrl:
    """Tests for store_credentials_in_database_url function."""

    @patch("src.utils.google_credentials.update_env_file")
    def test_store_credentials(self, mock_update_env, mock_credentials, mock_user_info):
        """Test storing credentials in DATABASE_URL."""
        result = store_credentials_in_database_url(mock_credentials, mock_user_info)
        assert result is True
        mock_update_env.assert_called_once()
        
        # Check that DATABASE_URL was set in environment
        database_url = os.environ.get("DATABASE_URL")
        assert database_url is not None
        
        # Verify the stored credentials
        stored_credentials = json.loads(database_url)
        assert stored_credentials["access_token"] == mock_credentials["access_token"]
        assert stored_credentials["refresh_token"] == mock_credentials["refresh_token"]
        assert stored_credentials["user_info"]["email"] == mock_user_info["email"]

    @patch("src.utils.google_credentials.update_env_file", side_effect=Exception("Test error"))
    def test_store_credentials_error(self, mock_update_env, mock_credentials, mock_user_info):
        """Test error handling when storing credentials."""
        result = store_credentials_in_database_url(mock_credentials, mock_user_info)
        assert result is False
        mock_update_env.assert_called_once()


class TestClearCredentialsFromDatabaseUrl:
    """Tests for clear_credentials_from_database_url function."""

    @patch("src.utils.google_credentials.update_env_file")
    def test_clear_credentials(self, mock_update_env, mock_env_with_database_url):
        """Test clearing credentials from DATABASE_URL."""
        result = clear_credentials_from_database_url()
        assert result is True
        mock_update_env.assert_called_once_with("DATABASE_URL", "")
        
        # Check that DATABASE_URL was cleared
        assert os.environ.get("DATABASE_URL") == ""

    @patch("src.utils.google_credentials.update_env_file")
    def test_clear_credentials_not_json(self, mock_update_env, mock_env_empty):
        """Test when DATABASE_URL is not JSON."""
        os.environ["DATABASE_URL"] = "postgres://user:pass@host:port/db"
        result = clear_credentials_from_database_url()
        assert result is True
        mock_update_env.assert_not_called()

    @patch("src.utils.google_credentials.update_env_file", side_effect=Exception("Test error"))
    def test_clear_credentials_error(self, mock_update_env, mock_env_with_database_url):
        """Test error handling when clearing credentials."""
        result = clear_credentials_from_database_url()
        assert result is False
        mock_update_env.assert_called_once()


class TestUpdateEnvFile:
    """Tests for update_env_file function."""

    @patch("builtins.open", new_callable=MagicMock)
    @patch("os.path.exists", return_value=True)
    def test_update_existing_key(self, mock_exists, mock_open, mock_env_empty):
        """Test updating an existing key in .env file."""
        # Mock file content
        mock_file = MagicMock()
        mock_file.__enter__.return_value.readlines.return_value = [
            "# Comment\n",
            "EXISTING_KEY=old_value\n",
            "OTHER_KEY=other_value\n"
        ]
        mock_open.return_value = mock_file

        result = update_env_file("EXISTING_KEY", "new_value")
        assert result is True
        
        # Check that file was written with updated content
        mock_file.__enter__.return_value.writelines.assert_called_once()
        written_lines = mock_file.__enter__.return_value.writelines.call_args[0][0]
        assert "EXISTING_KEY='new_value'\n" in written_lines
        assert "OTHER_KEY=other_value\n" in written_lines
        assert "# Comment\n" in written_lines

    @patch("builtins.open", new_callable=MagicMock)
    @patch("os.path.exists", return_value=True)
    def test_add_new_key(self, mock_exists, mock_open, mock_env_empty):
        """Test adding a new key to .env file."""
        # Mock file content
        mock_file = MagicMock()
        mock_file.__enter__.return_value.readlines.return_value = [
            "# Comment\n",
            "EXISTING_KEY=old_value\n"
        ]
        mock_open.return_value = mock_file

        result = update_env_file("NEW_KEY", "new_value")
        assert result is True
        
        # Check that file was written with new key
        mock_file.__enter__.return_value.writelines.assert_called_once()
        written_lines = mock_file.__enter__.return_value.writelines.call_args[0][0]
        assert "NEW_KEY='new_value'\n" in written_lines
        assert "EXISTING_KEY=old_value\n" in written_lines
        assert "# Comment\n" in written_lines

    @patch("builtins.open", new_callable=MagicMock)
    @patch("os.path.exists", return_value=False)
    def test_create_env_file(self, mock_exists, mock_open, mock_env_empty):
        """Test creating .env file if it doesn't exist."""
        # Mock file content
        mock_file = MagicMock()
        mock_file.__enter__.return_value.readlines.return_value = []
        mock_open.return_value = mock_file

        result = update_env_file("NEW_KEY", "new_value")
        assert result is True
        
        # Check that file was written with new key
        mock_file.__enter__.return_value.writelines.assert_called_once()
        written_lines = mock_file.__enter__.return_value.writelines.call_args[0][0]
        assert "NEW_KEY='new_value'\n" in written_lines

    @patch("builtins.open", side_effect=Exception("Test error"))
    @patch("os.path.exists", return_value=True)
    def test_file_error(self, mock_exists, mock_open, mock_env_empty):
        """Test error handling when updating .env file."""
        result = update_env_file("KEY", "value")
        assert result is False
