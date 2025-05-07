import asyncio
import json
from src.services.n8n_service import N8nService
from src.providers.google.transformers.workflow_transformer import GoogleWorkflowTransformer
import os
import httpx
import time

async def test_workflow():
    # Load test workflow
    with open('tests/fixtures/test_workflow.json') as f:
        workflow_data = json.load(f)
    
    # Initialize n8n service
    service = N8nService(
        api_url=os.getenv('N8N_API_URL'),
        api_key=os.getenv('N8N_API_KEY')
    )
    
    try:
        # First check connection
        print("\nChecking n8n connection...")
        connection = await service.check_connection()
        print("Connection status:", json.dumps(connection, indent=2))
        
        # Transform workflow
        print("\nTransforming workflow...")
        transformer = GoogleWorkflowTransformer()
        transformed_workflow = transformer.transform(workflow_data)
        print("Transformation complete")
        
        # Create workflow
        print("\nCreating workflow in n8n...")
        workflow_id = await service.create_workflow(transformed_workflow)
        print(f"Created workflow with ID: {workflow_id}")
        
        # Activate workflow
        print("\nActivating workflow...")
        await service.activate_workflow(workflow_id)
        print("Workflow activated")
        
        # Execute workflow via webhook
        print("\nExecuting workflow via webhook...")
        webhook_data = {
            "workflowData": {
                "1": {
                    "email": "test@example.com",
                    "preferredTime": "2024-04-24T10:00:00Z",
                    "company": "Test Company"
                }
            }
        }
        
        # Use the production webhook URL
        webhook_url = f"https://blopit.app.n8n.cloud/webhook/execute/{workflow_id}"
        async with httpx.AsyncClient() as client:
            response = await client.post(webhook_url, json=webhook_data)
            print(f"Webhook execution response: {response.status_code}")
            print(response.text)
            
        if response.status_code != 200:
            print("Error executing workflow via webhook")
            return False
            
        print("Workflow executed successfully")
        return True
            
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

if __name__ == "__main__":
    asyncio.run(test_workflow()) 