"""
Router for mantra-related endpoints.
This module handles API routes for:
- Creating new mantras
- Listing available mantras
- Installing mantras for users
- Managing mantra installations
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query, Body
from sqlalchemy.orm import Session
import logging
from pydantic import BaseModel
from sqlalchemy import select
from uuid import UUID

from src.utils.database import get_db
from src.services.mantra_service import MantraService
from src.services.n8n_service import N8nService
from src.utils.config import get_settings
from src.models.mantra import Mantra, MantraInstallation
from src.providers.google.transformers import GoogleWorkflowTransformer

router = APIRouter(
    prefix="/api/mantras",
    tags=["mantras"]
)

logger = logging.getLogger(__name__)

def get_test_session():
    """Get test session for testing."""
    return None

def get_n8n_service() -> N8nService:
    """Get N8N service instance."""
    settings = get_settings()
    return N8nService(settings.N8N_API_URL, settings.N8N_API_KEY)

class MantraCreate(BaseModel):
    name: str
    description: str
    user_id: str
    workflow_json: Dict[str, Any]
    is_active: bool = True

@router.post("/", response_model=Dict[str, Any])
async def create_mantra(
    request: Request,
    mantra: MantraCreate,
    db: Session = Depends(get_db),
    test_session: Optional[Dict[str, Any]] = Depends(get_test_session),
    n8n_service: N8nService = Depends(get_n8n_service)
):
    """Create a new mantra"""
    try:
        # Check if user is authenticated
        user = test_session.get("user") if test_session else request.session.get("user")
        if not user and not test_session:  # Skip auth check in test mode
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Please log in to create a workflow"
            )
            
        # Initialize service
        service = MantraService(db, n8n_service)

        # Create mantra
        mantra_obj = await service.create_mantra(
            name=mantra.name,
            description=mantra.description,
            workflow_json=mantra.workflow_json,
            user_id=mantra.user_id
        )
        return {"id": str(mantra_obj.id), "name": mantra_obj.name}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating mantra: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating mantra: {str(e)}"
        )

@router.get("/", response_model=List[Dict[str, Any]])
async def list_mantras(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    n8n_service: N8nService = Depends(get_n8n_service)
):
    """List all available mantras"""
    service = MantraService(db, n8n_service)
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
    db: Session = Depends(get_db),
    n8n_service: N8nService = Depends(get_n8n_service)
):
    """Get a specific mantra by ID"""
    service = MantraService(db, n8n_service)
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
    db: Session = Depends(get_db),
    n8n_service: N8nService = Depends(get_n8n_service)
):
    """Install a mantra for a user"""
    service = MantraService(db, n8n_service)
    try:
        installation = await service.install_mantra(mantra_id, user_id, config)
        return {
            "id": str(installation.id),
            "installation_id": str(installation.id),
            "mantra_id": str(installation.mantra_id),
            "status": installation.status,
            "config": installation.config
        }
    except HTTPException as e:
        # Re-raise HTTP exceptions
        raise e
    except Exception as e:
        logger.error(f"Error installing mantra: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error installing mantra: {str(e)}"
        )

@router.delete("/installations/{installation_id}")
async def uninstall_mantra(
    installation_id: UUID,
    db: Session = Depends(get_db),
    n8n_service: N8nService = Depends(get_n8n_service)
):
    """Uninstall a mantra"""
    service = MantraService(db, n8n_service)
    
    try:
        # Get the installation to get the user_id
        result = await db.execute(
            select(MantraInstallation).where(MantraInstallation.id == installation_id)
        )
        installation = result.scalar_one_or_none()
        if not installation:
            raise HTTPException(status_code=404, detail="Installation not found")
            
        if not installation.user_id:
            raise HTTPException(status_code=400, detail="Installation has no associated user")
            
        await service.uninstall_mantra(installation_id, installation.user_id)
        return {"message": "Mantra uninstalled successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uninstalling mantra: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error uninstalling mantra: {str(e)}")

@router.put("/installations/{installation_id}/status", response_model=Dict[str, Any])
async def update_installation_status(
    installation_id: str,
    status: str,
    db: Session = Depends(get_db),
    n8n_service: N8nService = Depends(get_n8n_service)
):
    """Update the status of an installed mantra"""
    service = MantraService(db, n8n_service)
    installation = service.update_mantra_status(installation_id, status)
    return {
        "installation_id": str(installation.id),
        "status": installation.status,
        "updated_at": installation.updated_at
    }

@router.get("/users/{user_id}", response_model=List[Dict[str, Any]])
async def get_user_mantras(
    user_id: str,
    db: Session = Depends(get_db),
    n8n_service: N8nService = Depends(get_n8n_service)
):
    """Get all mantras installed by a user"""
    service = MantraService(db, n8n_service)
    return service.get_user_mantras(user_id)

@router.post("/installations/{installation_id}/execute", response_model=Dict[str, Any])
async def execute_mantra(
    installation_id: UUID,
    data: Dict[str, Any],
    db: Session = Depends(get_db),
    n8n_service: N8nService = Depends(get_n8n_service)
):
    """Execute a mantra workflow"""
    service = MantraService(db, n8n_service)
    try:
        result = await service.execute_mantra_workflow(installation_id, data)
        return {
            "success": True,
            "result": {
                "execution_id": result.get("execution_id"),
                "output": result.get("output", {})
            },
            "installation_id": str(installation_id)
        }
    except HTTPException as e:
        # Re-raise HTTP exceptions
        raise e
    except Exception as e:
        logger.error(f"Error executing mantra workflow: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error executing mantra workflow: {str(e)}"
        )

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