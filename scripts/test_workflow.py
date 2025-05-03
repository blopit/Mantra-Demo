#!/usr/bin/env python3
import asyncio
import logging
import sys
from src.services.n8n_service import N8nService
import os
import httpx
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_health_check():
    """Test n8n service health check."""
    try:
        n8n_service = N8nService(
            api_url=os.getenv('N8N_API_URL'),
            api_key=os.getenv('N8N_API_KEY')
        )
        
        logger.info("Running health check...")
        result = await n8n_service.check_connection()
        
        logger.info("✅ Health check successful")
        logger.info(f"Status: {result['status']}")
        logger.info(f"Response time: {result.get('response_time_ms', 0)}ms")
        return True
    except Exception as e:
        logger.error(f"❌ Health check failed: {str(e)}")
        return False

async def test_list_workflows():
    """Test listing workflows."""
    try:
        n8n_service = N8nService(
            api_url=os.getenv('N8N_API_URL'),
            api_key=os.getenv('N8N_API_KEY')
        )
        
        logger.info("Listing workflows...")
        workflows = await n8n_service.list_workflows()
        
        logger.info("✅ Successfully retrieved workflows")
        logger.info(f"Total workflows: {len(workflows)}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to list workflows: {str(e)}")
        return False

async def test_workflow_creation():
    """Test creating and deleting a workflow."""
    try:
        n8n_service = N8nService(
            api_url=os.getenv('N8N_API_URL'),
            api_key=os.getenv('N8N_API_KEY')
        )
        
        logger.info("Creating test workflow...")
        
        # Create a simple workflow with a Schedule trigger and a NoOp node
        workflow = {
            "name": "Test Workflow",
            "nodes": [
                {
                    "parameters": {
                        "rule": {
                            "interval": [
                                {
                                    "field": "hours",
                                    "expression": "*/1"
                                }
                            ]
                        }
                    },
                    "name": "Schedule Trigger",
                    "type": "n8n-nodes-base.scheduleTrigger",
                    "typeVersion": 1,
                    "position": [250, 300]
                },
                {
                    "parameters": {},
                    "name": "NoOp",
                    "type": "n8n-nodes-base.noOp",
                    "typeVersion": 1,
                    "position": [460, 300]
                }
            ],
            "connections": {
                "Schedule Trigger": {
                    "main": [
                        [
                            {
                                "node": "NoOp",
                                "type": "main",
                                "index": 0
                            }
                        ]
                    ]
                }
            },
            "settings": {}
        }
        
        created_workflow = await n8n_service.create_workflow(workflow)
        logger.info(f"✅ Successfully created workflow with ID: {created_workflow.get('id')}")
        
        # Clean up - delete the workflow
        if created_workflow.get('id'):
            await n8n_service.delete_workflow(created_workflow['id'])
            logger.info("✅ Successfully deleted test workflow")
        
        return True
    except Exception as e:
        logger.error(f"❌ Failed to create/delete workflow: {str(e)}")
        return False

async def run_all_tests():
    """Run all tests."""
    logger.info("Starting all tests...")
    
    test_results = {
        'health_check': await test_health_check(),
        'list_workflows': await test_list_workflows(),
        'workflow_creation': await test_workflow_creation()
    }
    
    logger.info("\nTest Results Summary:")
    for test_name, passed in test_results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        logger.info(f"{test_name}: {status}")

if __name__ == "__main__":
    asyncio.run(run_all_tests()) 