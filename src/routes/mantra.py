"""
Router for mantra-related endpoints.
This module handles API routes for:
- Creating new mantras
- Listing available mantras
- Installing mantras for users
- Managing mantra installations
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.orm import Session
import logging

from src.utils.database import get_db
from src.services.mantra_service import MantraService
from src.models.mantra import Mantra, MantraInstallation
from src.providers.google.transformers import GoogleWorkflowTransformer

router = APIRouter(
    prefix="/api/mantras",
    tags=["mantras"]
)

logger = logging.getLogger(__name__)

# Test session dependency
async def get_test_session() -> Optional[Dict[str, Any]]:
    return None

@router.post("/", response_model=Dict[str, Any])
async def create_mantra(
    request: Request,
    name: str = Query(..., description="Name of the mantra"),
    description: str = Query(..., description="Description of the mantra"),
    user_id: str = Query(..., description="ID of the user creating the mantra"),
    workflow_json: Dict[str, Any] = None,
    db: Session = Depends(get_db),
    test_session: Optional[Dict[str, Any]] = Depends(get_test_session)
):
    """Create a new mantra"""
    # Check if user is authenticated
    user = test_session.get("user") if test_session else request.session.get("user")
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Please log in to create a workflow"
        )
    
    # Get workflow_json from request body
    if workflow_json is None:
        workflow_json = await request.json()
        
    service = MantraService(db)
    mantra = service.create_mantra(name, description, workflow_json, user_id)
    return {
        "id": str(mantra.id),
        "name": mantra.name,
        "description": mantra.description,
        "created_at": mantra.created_at,
        "user_id": mantra.user_id
    }

@router.get("/", response_model=List[Dict[str, Any]])
async def list_mantras(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List all available mantras"""
    service = MantraService(db)
    mantras = service.get_mantras(skip, limit)
    return [
        {
            "id": str(m.id),
            "name": m.name,
            "description": m.description,
            "created_at": m.created_at,
            "user_id": m.user_id
        }
        for m in mantras
    ]

@router.get("/{mantra_id}", response_model=Dict[str, Any])
async def get_mantra(
    mantra_id: str,
    db: Session = Depends(get_db)
):
    """Get a specific mantra by ID"""
    service = MantraService(db)
    mantra = service.get_mantra_by_id(mantra_id)
    return {
        "id": str(mantra.id),
        "name": mantra.name,
        "description": mantra.description,
        "workflow_json": mantra.workflow_json,
        "created_at": mantra.created_at,
        "user_id": mantra.user_id
    }

@router.post("/{mantra_id}/install", response_model=Dict[str, Any])
async def install_mantra(
    mantra_id: str,
    user_id: str,
    config: Optional[Dict[str, Any]] = None,
    db: Session = Depends(get_db)
):
    """Install a mantra for a user"""
    service = MantraService(db)
    installation = service.install_mantra(mantra_id, user_id, config)
    return {
        "installation_id": str(installation.id),
        "mantra_id": str(installation.mantra_id),
        "user_id": installation.user_id,
        "status": installation.status,
        "installed_at": installation.installed_at,
        "config": installation.config
    }

@router.delete("/installations/{installation_id}")
async def uninstall_mantra(
    installation_id: str,
    db: Session = Depends(get_db)
):
    """Uninstall a mantra"""
    service = MantraService(db)
    service.uninstall_mantra(installation_id)
    return {"message": "Mantra uninstalled successfully"}

@router.put("/installations/{installation_id}/status", response_model=Dict[str, Any])
async def update_installation_status(
    installation_id: str,
    status: str,
    db: Session = Depends(get_db)
):
    """Update the status of an installed mantra"""
    service = MantraService(db)
    installation = service.update_mantra_status(installation_id, status)
    return {
        "installation_id": str(installation.id),
        "status": installation.status,
        "updated_at": installation.updated_at
    }

@router.get("/users/{user_id}", response_model=List[Dict[str, Any]])
async def get_user_mantras(
    user_id: str,
    db: Session = Depends(get_db)
):
    """Get all mantras installed by a user"""
    service = MantraService(db)
    return service.get_user_mantras(user_id)

@router.post("/installations/{installation_id}/execute", response_model=Dict[str, Any])
async def execute_mantra(
    installation_id: str,
    data: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """Execute a mantra workflow"""
    service = MantraService(db)
    return service.execute_mantra_workflow(installation_id, data)

@router.post("/test-workflow")
async def test_workflow_transformation():
    """
    Test endpoint to transform a sample workflow
    """
    try:
        # Sample workflow for testing
        test_workflow = {
            "nodes": [
                {
                    "id": "1",
                    "type": "gmail",
                    "name": "Send Email",
                    "parameters": {
                        "operation": "sendEmail",
                        "to": "{{'{{trigger.email}}'}}",
                        "subject": "Welcome to Mantra!",
                        "text": "Thanks for trying out our workflow automation!"
                    }
                },
                {
                    "id": "2",
                    "type": "googleCalendar",
                    "name": "Create Event",
                    "parameters": {
                        "operation": "createEvent",
                        "calendar": "primary",
                        "summary": "Onboarding Call",
                        "description": "Welcome call with new user",
                        "start": "{{'{{trigger.preferredTime}}'}}",
                        "end": "{{'{{addHours(trigger.preferredTime, 1)}}'}}",
                    }
                },
                {
                    "id": "3",
                    "type": "googleDrive",
                    "name": "Create Folder",
                    "parameters": {
                        "operation": "createFolder",
                        "name": "{{'{{trigger.company}}'}} Resources",
                        "parent": "root"
                    }
                }
            ],
            "connections": {
                "Send Email": {
                    "main": [["Create Event", 0]]
                },
                "Create Event": {
                    "main": [["Create Folder", 0]]
                }
            },
            "trigger": {
                "type": "webhook",
                "parameters": {
                    "email": {"type": "string"},
                    "company": {"type": "string"},
                    "preferredTime": {"type": "string", "format": "date-time"}
                }
            }
        }
        
        # Transform the workflow
        transformer = GoogleWorkflowTransformer()
        transformed = transformer.transform_workflow(test_workflow)
        
        return {
            "status": "success",
            "message": "Workflow transformed successfully",
            "workflow": transformed
        }
        
    except Exception as e:
        logger.error(f"Error transforming workflow: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error transforming workflow: {str(e)}"
        ) 