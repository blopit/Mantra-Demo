"""
Test script for the Google workflow transformer.
"""
import logging
from .workflow_transformer import GoogleWorkflowTransformer
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO)

# Sample email summary workflow
sample_email_summary_workflow = {
    "name": "Email Summary Agent",
    "nodes": [
        {
            "id": "1",
            "name": "Gmail",
            "type": "n8n-nodes-base.gmail",
            "typeVersion": 1,
            "position": [1140, 380],
            "parameters": {
                "operation": "getAll",
                "userId": "me",
                "labelIds": ["INBOX"],
                "q": "after:{{$now.minus(1).day}}",
                "maxResults": 100
            }
        },
        {
            "id": "2",
            "name": "Organize Email Data",
            "type": "n8n-nodes-base.aggregate",
            "typeVersion": 1,
            "position": [1320, 380],
            "parameters": {
                "aggregate": "aggregateAllItemData",
                "include": "specifiedFields",
                "fieldsToInclude": "id, From, To, CC, snippet",
                "options": {}
            }
        },
        {
            "id": "3",
            "name": "Send Summary",
            "type": "n8n-nodes-base.gmail",
            "typeVersion": 1,
            "position": [1680, 380],
            "parameters": {
                "operation": "sendEmail",
                "to": "test@example.com",
                "subject": "Daily Email Summary",
                "text": "={{ $node[\"Organize Email Data\"].json }}"
            }
        }
    ],
    "connections": {
        "Gmail": {
            "main": [
                [
                    {
                        "node": "Organize Email Data",
                        "type": "main",
                        "index": 0
                    }
                ]
            ]
        },
        "Organize Email Data": {
            "main": [
                [
                    {
                        "node": "Send Summary",
                        "type": "main",
                        "index": 0
                    }
                ]
            ]
        }
    }
}

def test_email_summary_workflow_transformation():
    """Test the transformation of the email summary workflow."""
    transformer = GoogleWorkflowTransformer()
    
    # Transform the workflow
    transformed = transformer.transform_workflow(sample_email_summary_workflow)
    
    # Basic workflow structure checks
    assert transformed["name"] == "Email Summary Agent"
    assert "nodes" in transformed
    assert "connections" in transformed
    assert "settings" in transformed
    assert transformed["settings"]["executionOrder"] == "v1"
    
    # Verify nodes exist and are in correct order
    nodes = transformed["nodes"]
    assert len(nodes) >= 7  # At least 7 nodes (trigger, credentials, token, etc.)
    
    # Check webhook trigger node
    trigger_nodes = [
        node for node in nodes 
        if node["type"] == "n8n-nodes-base.webhook"
    ]
    assert len(trigger_nodes) == 1  # Should only have one trigger node
    trigger_node = trigger_nodes[0]
    assert trigger_node["typeVersion"] == 1
    assert trigger_node["name"] == "Webhook Trigger"
    assert "webhookId" in trigger_node
    assert trigger_node["parameters"]["path"] == "dummy-trigger"
    assert trigger_node["parameters"]["responseMode"] == "responseNode"
    
    # Check credentials nodes
    credentials_node = next(
        (node for node in nodes if node["name"].endswith("Credentials")),
        None
    )
    assert credentials_node is not None
    assert credentials_node["type"] == "n8n-nodes-base.set"
    assert "client_id" in str(credentials_node["parameters"])
    assert "client_secret" in str(credentials_node["parameters"])
    assert "refresh_token" in str(credentials_node["parameters"])
    
    # Check token nodes
    token_request_node = next(
        (node for node in nodes if "Access Token" in node["name"] and node["type"] == "n8n-nodes-base.httpRequest"),
        None
    )
    assert token_request_node is not None
    assert token_request_node["parameters"]["url"] == "https://oauth2.googleapis.com/token"
    
    # Check Gmail API nodes
    fetch_emails_node = next(
        (node for node in nodes if "Fetch Emails" in node["name"]),
        None
    )
    assert fetch_emails_node is not None
    assert fetch_emails_node["type"] == "n8n-nodes-base.httpRequest"
    assert "gmail.googleapis.com" in fetch_emails_node["parameters"]["url"]
    
    # Check data processing nodes
    organize_node = next(
        (node for node in nodes if "Organize Email Data" in node["name"]),
        None
    )
    assert organize_node is not None
    assert organize_node["type"] == "n8n-nodes-base.aggregate"
    
    # Check encoding node
    encode_node = next(
        (node for node in nodes if "Encode" in node["name"]),
        None
    )
    assert encode_node is not None
    assert encode_node["type"] == "n8n-nodes-base.function"
    
    # Check send email node
    send_node = next(
        (node for node in nodes if "Send Summary" in node["name"]),
        None
    )
    assert send_node is not None
    assert send_node["type"] == "n8n-nodes-base.httpRequest"
    assert "gmail.googleapis.com" in send_node["parameters"]["url"]
    
    # Verify connections
    connections = transformed["connections"]
    
    # Check trigger connection
    trigger_connections = connections.get(trigger_node["id"], {}).get("main", [[]])[0]
    assert len(trigger_connections) > 0
    assert trigger_connections[0]["node"] == credentials_node["name"]
    
    # Check credentials connection
    credentials_connections = connections.get(credentials_node["id"], {}).get("main", [[]])[0]
    assert len(credentials_connections) > 0
    assert credentials_connections[0]["node"] == token_request_node["name"]
    
    # Check complete chain of connections
    def get_next_node(current_node_name):
        for node_id, conn in connections.items():
            if any(c["node"] == current_node_name for c in conn.get("main", [[]])[0]):
                return next(node for node in nodes if node["id"] == node_id)
        return None
    
    # Verify the chain of connections
    current_node = trigger_node
    expected_sequence = [
        "Credentials",
        "Access Token",
        "Access Token",
        "Fetch Emails",
        "Organize Email Data",
        "Encode",
        "Send Summary"
    ]
    
    for expected in expected_sequence:
        current_node = get_next_node(current_node["name"])
        assert current_node is not None
        assert any(expected in current_node["name"] for expected in expected_sequence)

def main():
    """Run the workflow transformer test."""
    logging.info("Running workflow transformer tests...")
    
    try:
        test_email_summary_workflow_transformation()
        logging.info("✓ Email summary workflow transformation test passed")
        
        logging.info("All tests passed successfully!")
        
    except AssertionError as e:
        logging.error(f"Test failed: {str(e)}")
    except Exception as e:
        logging.error(f"Error during tests: {str(e)}")

if __name__ == "__main__":
    main() 