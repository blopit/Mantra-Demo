#!/usr/bin/env python3
import asyncio
import logging
import sys
from src.services.n8n_service import N8nService
from src.services.mantra_service import MantraService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def check_n8n_connection():
    """Check N8N service connection and print detailed diagnostics."""
    try:
        # Create N8N service instance
        n8n_service = N8nService(
            api_url="https://blopit.app.n8n.cloud",  # Replace with your N8N URL
            api_key="test_api_key"  # Replace with your N8N API key
        )
        
        logger.info("Checking N8N service connection...")
        
        # Try to connect
        result = await n8n_service.check_connection()
        
        if result["is_connected"]:
            logger.info("✅ Successfully connected to N8N service")
            logger.info(f"Status: {result.get('status')}")
            logger.info(f"Version: {result.get('version')}")
            logger.info(f"Response time: {result.get('response_time_ms')}ms")
            return True
        else:
            logger.error("❌ Failed to connect to N8N service")
            logger.error(f"Error: {result.get('error')}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error checking N8N connection: {str(e)}")
        return False

async def run_diagnostics():
    """Run a series of diagnostic checks."""
    logger.info("Running N8N service diagnostics...")
    
    # Check environment variables
    env_vars = {
        "N8N_API_URL": "API URL",
        "N8N_API_KEY": "API Key",
        "N8N_API_TIMEOUT": "API Timeout",
        "N8N_MAX_RETRIES": "Max Retries",
        "N8N_RETRY_DELAY": "Retry Delay"
    }
    
    logger.info("\nChecking environment variables:")
    for var, desc in env_vars.items():
        import os
        value = os.getenv(var)
        if value:
            # Mask sensitive values
            if "KEY" in var:
                value = "*" * len(value)
            logger.info(f"✅ {desc} ({var}): {value}")
        else:
            logger.error(f"❌ {desc} ({var}) is not set")
    
    # Check N8N service connection
    logger.info("\nChecking N8N service connection:")
    connection_success = await check_n8n_connection()
    
    if not connection_success:
        logger.info("\nTroubleshooting tips:")
        logger.info("1. Verify N8N is running and accessible")
        logger.info("2. Check if the N8N API URL is correct")
        logger.info("3. Verify the API key is valid")
        logger.info("4. Check network connectivity")
        logger.info("5. Verify N8N service is healthy")
        logger.info("6. Check firewall settings")
        logger.info("7. Verify SSL/TLS configuration if using HTTPS")

if __name__ == "__main__":
    try:
        asyncio.run(run_diagnostics())
    except KeyboardInterrupt:
        logger.info("\nDiagnostics interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\nFailed to run diagnostics: {str(e)}")
        sys.exit(1) 