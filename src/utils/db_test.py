"""
Database connection testing utility.

This module provides functions to test database connections and ensure
that the application can connect to both SQLite and PostgreSQL databases.
"""

import os
import logging
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from src.utils.database import get_engine, get_database_url
from src.utils.logger import get_logger

logger = get_logger(__name__)

def test_database_connection():
    """
    Test the database connection to ensure it's working properly.
    
    This function attempts to connect to the database and execute a simple
    query to verify that the connection is working. It logs the result
    and returns a boolean indicating success or failure.
    
    Returns:
        bool: True if the connection is successful, False otherwise
    """
    try:
        # Get the database URL and create an engine
        db_url = get_database_url()
        engine = get_engine(db_url)
        
        # Log the database type
        db_type = "SQLite" if db_url.startswith("sqlite") else "PostgreSQL"
        logger.info(f"Testing connection to {db_type} database at {db_url}")
        
        # Execute a simple query to test the connection
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            row = result.fetchone()
            if row and row[0] == 1:
                logger.info(f"Successfully connected to {db_type} database")
                return True
            else:
                logger.error(f"Connection test failed for {db_type} database")
                return False
    
    except SQLAlchemyError as e:
        logger.error(f"Database connection error: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error testing database connection: {str(e)}")
        return False

def switch_database_environment(environment):
    """
    Switch the database environment between development and production.
    
    This function sets the ENVIRONMENT environment variable to switch
    between development and production database configurations.
    
    Args:
        environment (str): The environment to switch to ('development' or 'production')
        
    Returns:
        bool: True if the switch was successful, False otherwise
    """
    if environment not in ['development', 'production']:
        logger.error(f"Invalid environment: {environment}. Must be 'development' or 'production'")
        return False
    
    # Set the environment variable
    os.environ['ENVIRONMENT'] = environment
    logger.info(f"Switched to {environment} environment")
    
    # Test the connection with the new environment
    return test_database_connection()

if __name__ == "__main__":
    # This allows running this module directly to test the database connection
    import sys
    
    # Set up logging to console
    logging.basicConfig(level=logging.INFO)
    
    # Check if an environment argument was provided
    if len(sys.argv) > 1 and sys.argv[1] in ['development', 'production']:
        environment = sys.argv[1]
        success = switch_database_environment(environment)
    else:
        # Test the current environment
        success = test_database_connection()
    
    # Exit with appropriate status code
    sys.exit(0 if success else 1)
