"""
Router for mantra-related endpoints.
This module handles API routes for:
- Creating new mantras
- Listing available mantras
- Installing mantras for users
- Managing mantra installations
"""

import json
import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query, Body
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from sqlalchemy import select
from uuid import UUID
from datetime import datetime

from src.utils.database import get_db
from src.services.mantra_service import MantraService
from src.services.n8n_service import N8nService
from src.utils.config import get_settings
from src.models.mantra import Mantra, MantraInstallation
from src.providers.google.transformers import GoogleWorkflowTransformer
from src.utils.api_response import success_response, error_response
from src.exceptions import MantraError, MantraNotFoundError

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

class MantraResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    user_id: str
    is_active: bool
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True
        json_encoders = {
            UUID: str,
            datetime: lambda dt: dt.isoformat() if dt else None
        }

@router.post("/")
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
            return JSONResponse(
                content=error_response(
                    message="Please log in to create a workflow",
                    code="unauthorized"
                ),
                status_code=status.HTTP_401_UNAUTHORIZED
            )

        # Validate workflow JSON
        if not isinstance(mantra.workflow_json, dict) or "nodes" not in mantra.workflow_json:
            return JSONResponse(
                content=error_response(
                    message="Invalid workflow JSON: must contain 'nodes' field",
                    code="validation_error"
                ),
                status_code=status.HTTP_400_BAD_REQUEST
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

        return JSONResponse(
            content=success_response(
                data={"id": str(mantra_obj.id), "name": mantra_obj.name},
                message="Mantra created successfully"
            ),
            status_code=status.HTTP_201_CREATED
        )
    except ValueError as e:
        logger.error(f"Validation error in create_mantra: {str(e)}")
        return JSONResponse(
            content=error_response(
                message=str(e),
                code="validation_error"
            ),
            status_code=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f"Error creating mantra: {str(e)}", exc_info=True)  # Added exc_info for full traceback
        return JSONResponse(
            content=error_response(
                message=f"Error creating mantra: {str(e)}",
                code="server_error"
            ),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@router.get("/")
async def list_mantras(
    skip: int = Query(0, description="Number of records to skip"),
    limit: int = Query(100, description="Maximum number of records to return"),
    db: Session = Depends(get_db),
    n8n_service: N8nService = Depends(get_n8n_service)
):
    """List all available mantras"""
    try:
        service = MantraService(db, n8n_service)
        mantras = await service.get_mantras(skip, limit)

        mantra_list = [MantraResponse.model_validate(m) for m in mantras]
        
        # Convert to dict with proper UUID and datetime serialization
        serialized_mantras = []
        for m in mantra_list:
            mantra_dict = m.model_dump()
            mantra_dict["id"] = str(mantra_dict["id"])  # Convert UUID to string
            if mantra_dict.get("created_at"):
                mantra_dict["created_at"] = mantra_dict["created_at"].isoformat()
            if mantra_dict.get("updated_at"):
                mantra_dict["updated_at"] = mantra_dict["updated_at"].isoformat()
            serialized_mantras.append(mantra_dict)

        return JSONResponse(
            content=success_response(
                data={
                    "mantras": serialized_mantras,
                    "count": len(serialized_mantras),
                    "skip": skip,
                    "limit": limit
                }
            )
        )
    except Exception as e:
        logger.error(f"Error listing mantras: {str(e)}")
        return JSONResponse(
            content=error_response(
                message=f"Error listing mantras: {str(e)}",
                code="server_error"
            ),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@router.get("/{mantra_id}")
async def get_mantra(
    mantra_id: str,
    db: Session = Depends(get_db),
    n8n_service: N8nService = Depends(get_n8n_service)
):
    """Get a specific mantra by ID"""
    try:
        service = MantraService(db, n8n_service)
        mantra = await service.get_mantra(mantra_id)
        
        # Convert to MantraResponse for proper serialization
        mantra_response = MantraResponse.model_validate(mantra)
        mantra_dict = mantra_response.model_dump()
        mantra_dict["id"] = str(mantra_dict["id"])  # Convert UUID to string
        if mantra_dict.get("created_at"):
            mantra_dict["created_at"] = mantra_dict["created_at"].isoformat()
        if mantra_dict.get("updated_at"):
            mantra_dict["updated_at"] = mantra_dict["updated_at"].isoformat()

        return JSONResponse(
            content=success_response(
                data=mantra_dict
            )
        )
    except MantraNotFoundError as e:
        return JSONResponse(
            content=error_response(
                message=str(e) or f"Mantra with ID {mantra_id} not found",
                code="not_found"
            ),
            status_code=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Error retrieving mantra: {str(e)}")
        return JSONResponse(
            content=error_response(
                message=f"Error retrieving mantra: {str(e)}",
                code="server_error"
            ),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

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
    installation = await service.update_mantra_status(installation_id, status)
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
    try:
        service = MantraService(db, n8n_service)
        installations = await service.get_user_installations(user_id)
        
        # Convert installations to dict with proper UUID and datetime serialization
        serialized_installations = []
        for installation in installations:
            installation_dict = {
                "id": str(installation.id),
                "mantra_id": str(installation.mantra_id),
                "user_id": installation.user_id,
                "installed_at": installation.installed_at.isoformat() if installation.installed_at else None,
                "status": installation.status,
                "config": installation.config,
                "n8n_workflow_id": installation.n8n_workflow_id,
                "is_active": installation.is_active,
                "disconnected_at": installation.disconnected_at.isoformat() if installation.disconnected_at else None
            }
            serialized_installations.append(installation_dict)
            
        return serialized_installations
    except Exception as e:
        logger.error(f"Error getting user mantras: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting user mantras: {str(e)}"
        )

@router.post("/installations/{installation_id}/execute")
async def execute_mantra(
    installation_id: UUID,
    data: Dict[str, Any],
    db: Session = Depends(get_db),
    n8n_service: N8nService = Depends(get_n8n_service)
):
    """Execute a mantra workflow using n8n API directly.

    This endpoint bypasses web interface authentication and uses the n8n API key directly.
    The n8n service handles its own authentication using the API key.
    """
    try:
        # Initialize service with n8n API key
        service = MantraService(db, n8n_service)

        # Execute workflow using n8n API directly
        result = await service.execute_mantra_workflow(installation_id, data)

        return JSONResponse(
            content=success_response(
                data={
                    "result": {
                        "execution_id": result.get("execution_id"),
                        "output": result.get("output", {})
                    },
                    "installation_id": str(installation_id)
                },
                message="Workflow executed successfully"
            )
        )
    except HTTPException as e:
        # Convert HTTP exceptions to our standard format
        return JSONResponse(
            content=error_response(
                message=e.detail,
                code="execution_error"
            ),
            status_code=e.status_code
        )
    except Exception as e:
        logger.error(f"Error executing mantra workflow: {str(e)}")
        return JSONResponse(
            content=error_response(
                message=f"Error executing mantra workflow: {str(e)}",
                code="server_error"
            ),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
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