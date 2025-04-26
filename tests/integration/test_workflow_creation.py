"""
Test script for workflow creation and execution.
"""
import json
import requests
from requests.sessions import Session
from itsdangerous import URLSafeTimedSerializer
from datetime import datetime, timedelta
import os
import pathlib

# Server URL
BASE_URL = "http://localhost:8000"

def load_workflow_fixture():
    """Load the test workflow fixture."""
    fixture_path = pathlib.Path(__file__).parent.parent / "fixtures" / "test_workflow.json"
    with open(fixture_path) as f:
        return json.load(f)

def test_workflow_creation():
    """Test creating and executing a workflow."""
    # Create a session to maintain cookies
    session = Session()
    
    # Create test user
    test_user = {
        "id": "test123",
        "email": "test@example.com",
        "name": "Test User",
        "picture": "https://example.com/test.jpg"
    }
    
    # Sign the session data using the same secret key as in app.py
    serializer = URLSafeTimedSerializer(os.getenv("SESSION_SECRET_KEY", "your-secret-key-here"))
    session_data = {
        "user": test_user,
        "tokens": {
            "access_token": "test_access_token",
            "refresh_token": "test_refresh_token",
            "id_token": "test_id_token"
        }
    }
    signed_session = serializer.dumps(session_data)
    
    # Set the session cookie
    session.cookies.set("session", signed_session)
    
    # Load test workflow from fixture
    workflow_data = load_workflow_fixture()
    
    # Create workflow
    create_response = session.post(
        f"{BASE_URL}/api/mantras/",
        json={
            "name": workflow_data["name"],
            "description": workflow_data["description"],
            "workflow_json": workflow_data["workflow_json"],
            "user_id": test_user["id"]
        }
    )
    
    print(f"Create workflow response: {create_response.status_code}")
    print(create_response.json())
    
    if create_response.status_code == 200:
        mantra_id = create_response.json()["id"]
        
        # Install workflow
        install_response = session.post(
            f"{BASE_URL}/api/mantras/{mantra_id}/install",
            json={"user_id": test_user["id"]}
        )
        
        print(f"Install workflow response: {install_response.status_code}")
        print(install_response.json())
        
        if install_response.status_code == 200:
            installation_id = install_response.json()["id"]
            
            # Execute workflow with ISO formatted datetime
            preferred_time = (datetime.now() + timedelta(days=1)).replace(hour=10, minute=0).isoformat()
            execute_response = session.post(
                f"{BASE_URL}/api/mantras/installations/{installation_id}/execute",
                json={
                    "email": test_user["email"],
                    "preferredTime": preferred_time
                }
            )
            
            print(f"Execute workflow response: {execute_response.status_code}")
            print(execute_response.json())

if __name__ == "__main__":
    test_workflow_creation() 