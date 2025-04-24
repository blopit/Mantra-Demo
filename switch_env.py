#!/usr/bin/env python
"""
Environment switching utility for Mantra Demo.

This script allows users to easily switch between development and production
environments, testing the database connection in the process.

Usage:
    python switch_env.py development
    python switch_env.py production
"""

import os
import sys
import logging
from src.utils.db_test import switch_database_environment, test_database_connection

def main():
    """Main entry point for the script."""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger("switch_env")
    
    # Check arguments
    if len(sys.argv) != 2 or sys.argv[1] not in ['development', 'production', 'test']:
        logger.error("Usage: python switch_env.py [development|production|test]")
        return 1
    
    environment = sys.argv[1]
    
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
        try:
            with open('.env', 'r') as f:
                env_content = f.read()
            
            # Replace ENVIRONMENT line
            if 'ENVIRONMENT=' in env_content:
                env_content = '\n'.join([
                    line if not line.startswith('ENVIRONMENT=') else f'ENVIRONMENT={environment}'
                    for line in env_content.split('\n')
                ])
            else:
                # Add ENVIRONMENT line if it doesn't exist
                env_content += f'\nENVIRONMENT={environment}\n'
            
            # Write updated content
            with open('.env', 'w') as f:
                f.write(env_content)
                
            logger.info(f"Updated .env file with ENVIRONMENT={environment}")
        except Exception as e:
            logger.error(f"Failed to update .env file: {e}")
            return 1
        
        return 0
    else:
        logger.error(f"Failed to switch to {environment} environment")
        return 1

if __name__ == "__main__":
    sys.exit(main())
