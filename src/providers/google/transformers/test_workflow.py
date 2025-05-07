"""
Test script for the Google workflow transformer.
"""
import logging
from .workflow_transformer import GoogleWorkflowTransformer

# Configure logging
logging.basicConfig(level=logging.INFO)

# Sample n8n workflow with Google nodes and triggers
sample_workflow = {
    "nodes": [
        {
            "id": "1",
            "type": "n8n-nodes-base.webhook",
            "name": "Webhook",
            "parameters": {
                "path": "onboarding",
                "responseMode": "responseNode",
                "options": {}
            }
        },
        {
            "id": "2",
            "type": "gmail",
            "name": "Gmail",
            "parameters": {
                "operation": "sendEmail",
                "to": "test@example.com",
                "subject": "Test Email",
                "text": "This is a test email"
            }
        },
        {
            "id": "3",
            "type": "googleCalendar",
            "name": "Google Calendar",
            "parameters": {
                "operation": "createEvent",
                "calendar": "primary",
                "summary": "Test Event",
                "start": "2024-04-24T10:00:00",
                "end": "2024-04-24T11:00:00"
            }
        }
    ],
    "connections": {
        "Webhook": {
            "main": [
                [
                    {
                        "node": "Gmail",
                        "type": "main",
                        "index": 0
                    }
                ]
            ]
        },
        "Gmail": {
            "main": [
                [
                    {
                        "node": "Google Calendar",
                        "type": "main",
                        "index": 0
                    }
                ]
            ]
        }
    }
}

def test_trigger_transformation():
    """Test webhook/trigger node transformation."""
    transformer = GoogleWorkflowTransformer()
    transformed = transformer.transform_workflow(sample_workflow)
    
    # Verify webhook node was transformed
    webhook_node = next(
        (node for node in transformed['nodes'] if node['id'] == '1'),
        None
    )
    assert webhook_node is not None
    assert webhook_node['type'] == 'n8n-nodes-base.executeWorkflow'
    assert webhook_node['parameters']['executionMode'] == 'manually'
    
    # Verify metadata was stored
    metadata = transformer.get_node_metadata('1')
    assert metadata is not None
    assert metadata['original_type'] == 'n8n-nodes-base.webhook'
    assert metadata['transformed_type'] == 'n8n-nodes-base.executeWorkflow'

def test_google_node_transformation():
    """Test Google service node transformation."""
    transformer = GoogleWorkflowTransformer()
    transformed = transformer.transform_workflow(sample_workflow)
    
    # Verify Gmail node was transformed
    gmail_node = next(
        (node for node in transformed['nodes'] if node['id'] == '2'),
        None
    )
    assert gmail_node is not None
    assert gmail_node['type'] == 'n8n-nodes-base.gmail'
    
    # Verify Calendar node was transformed
    calendar_node = next(
        (node for node in transformed['nodes'] if node['id'] == '3'),
        None
    )
    assert calendar_node is not None
    assert calendar_node['type'] == 'n8n-nodes-base.googleCalendar'

def main():
    """Run the workflow transformer test."""
    logging.info("Running workflow transformer tests...")
    
    try:
        test_trigger_transformation()
        logging.info("✓ Trigger transformation test passed")
        
        test_google_node_transformation()
        logging.info("✓ Google node transformation test passed")
        
        logging.info("All tests passed successfully!")
        
    except AssertionError as e:
        logging.error(f"Test failed: {str(e)}")
    except Exception as e:
        logging.error(f"Error during tests: {str(e)}")

if __name__ == "__main__":
    main() 