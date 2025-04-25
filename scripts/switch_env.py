#!/usr/bin/env python
"""
Enhanced environment switching utility for Mantra Demo.

This script provides a robust way to switch between development, testing,
and production environments, with automatic database connection testing
and environment variable management.

Usage:
    python scripts/switch_env.py development   # Switch to development environment
    python scripts/switch_env.py production    # Switch to production environment
    python scripts/switch_env.py test          # Test current database connection
    python scripts/switch_env.py --help        # Show help message
"""

import os
import sys
import logging
import argparse
import shutil
from pathlib import Path
from dotenv import load_dotenv, set_key

from src.utils.db_test import switch_database_environment, test_database_connection

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/environment.log")
    ]
)
logger = logging.getLogger("switch_env")

# Ensure logs directory exists
os.makedirs("logs", exist_ok=True)

# Load environment variables
load_dotenv()

def backup_env_file():
    """Create a backup of the .env file."""
    env_path = Path(".env")
    backup_path = Path(".env.bak")

    if env_path.exists():
        try:
            shutil.copy2(env_path, backup_path)
            logger.info(f"Created backup of .env file at {backup_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to create backup of .env file: {e}")
            return False
    else:
        logger.warning("No .env file found to backup")
        return False

def update_env_file(environment):
    """
    Update the .env file with the new environment.

    Args:
        environment (str): The environment to switch to

    Returns:
        bool: True if successful, False otherwise
    """
    # First create a backup
    backup_success = backup_env_file()
    if not backup_success:
        logger.warning("Proceeding without backup")

    try:
        # Update ENVIRONMENT variable in .env file
        env_path = ".env"

        # Check if .env file exists
        if not os.path.exists(env_path):
            # Create a new .env file with the environment
            with open(env_path, "w") as f:
                f.write(f"ENVIRONMENT={environment}\n")
            logger.info(f"Created new .env file with ENVIRONMENT={environment}")
            return True

        # Update existing .env file
        set_key(env_path, "ENVIRONMENT", environment)
        logger.info(f"Updated .env file with ENVIRONMENT={environment}")

        # Also update ENV variable for compatibility
        set_key(env_path, "ENV", environment)

        return True
    except Exception as e:
        logger.error(f"Failed to update .env file: {e}")
        return False

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Switch between development and production environments",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.split("\n\n")[1]  # Use the usage examples from the docstring
    )

    parser.add_argument(
        "environment",
        choices=["development", "production", "test"],
        help="Environment to switch to, or 'test' to test current connection"
    )

    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip creating a backup of the .env file"
    )

    args = parser.parse_args()
    environment = args.environment

    # If just testing, don't switch environments
    if environment == 'test':
        logger.info("Testing current database connection...")
        success = test_database_connection()
        logger.info(f"Database connection test {'succeeded' if success else 'failed'}")
        return 0 if success else 1

    # Switch environment
    logger.info(f"Switching to {environment} environment...")
    success = switch_database_environment(environment)

    if success:
        logger.info(f"Successfully switched to {environment} environment")

        # Update .env file
        if update_env_file(environment):
            logger.info(f"Environment successfully switched to {environment}")
            return 0
        else:
            logger.error("Failed to update environment variables")
            return 1
    else:
        logger.error(f"Failed to switch to {environment} environment")
        return 1

if __name__ == "__main__":
    sys.exit(main())
