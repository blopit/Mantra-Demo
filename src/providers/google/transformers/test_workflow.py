"""
Test script for the Google workflow transformer.
"""
import logging
from workflow_transformer import GoogleWorkflowTransformer

# Configure logging
logging.basicConfig(level=logging.INFO)

# Sample n8n workflow with Google nodes
sample_workflow = {
    "nodes": [
        {
            "id": "1",
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
            "id": "2",
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

def main():
    """Run the workflow transformer test."""
    transformer = GoogleWorkflowTransformer()
    
    try:
        # Transform the workflow
        transformed_workflow = transformer.transform_workflow(sample_workflow)
        logging.info("Workflow transformation completed successfully")
        
    except Exception as e:
        logging.error(f"Error during workflow transformation: {str(e)}")

if __name__ == "__main__":
    main() 