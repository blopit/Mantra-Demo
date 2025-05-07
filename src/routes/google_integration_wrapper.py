"""
Wrapper for Google integration routes.

This module wraps the auto-generated google_integration.py routes
to provide standardized API responses.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from fastapi.responses import JSONResponse
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
import logging
from sqlalchemy import select
from sqlalchemy.sql import and_
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from src.utils.database import get_db
from src.models.google_integration import GoogleIntegration
from src.schemas.google_integration import GoogleIntegrationBase, GoogleIntegrationCreate, GoogleIntegrationUpdate, GoogleIntegrationResponse
from src.utils.api_response import success_response, error_response

# Import the original router to access its route handlers
from src.routes.google_integration import (
    get_google_integration_list as original_get_list,
    get_google_integration as original_get,
    create_google_integration as original_create,
    update_google_integration as original_update,
    delete_google_integration as original_delete
)

router = APIRouter(prefix="/api/google-integrations", tags=["GoogleIntegration"])
logger = logging.getLogger(__name__)


@router.get("/")
async def get_google_integration_list(
    skip: int = Query(0, description="Number of records to skip"),
    limit: int = Query(100, description="Maximum number of records to return"),
    db: Session = Depends(get_db)
):
    """Retrieve all Google integrations with standardized response format"""
    try:
        # Call the original handler
        items = await original_get_list(skip=skip, limit=limit, db=db)
        
        # Convert to dict for JSON serialization
        items_dict = [item.dict() for item in items]
        
        return JSONResponse(
            content=success_response(
                data={
                    "integrations": items_dict,
                    "count": len(items_dict),
                    "skip": skip,
                    "limit": limit
                }
            )
        )
    except HTTPException as e:
        return JSONResponse(
            content=error_response(
                message=e.detail,
                code="database_error" if e.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR else "request_error"
            ),
            status_code=e.status_code
        )
    except Exception as e:
        logger.error(f"Unexpected error in get_google_integration_list: {e}")
        return JSONResponse(
            content=error_response(
                message="An unexpected error occurred",
                code="server_error"
            ),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.get("/{integration_id}")
async def get_google_integration(
    integration_id: str,
    db: Session = Depends(get_db)
):
    """Retrieve a specific Google integration by ID with standardized response format"""
    try:
        # Call the original handler
        item = await original_get(integration_id=integration_id, db=db)
        
        return JSONResponse(
            content=success_response(
                data=item.dict()
            )
        )
    except HTTPException as e:
        return JSONResponse(
            content=error_response(
                message=e.detail,
                code="not_found" if e.status_code == status.HTTP_404_NOT_FOUND else "database_error"
            ),
            status_code=e.status_code
        )
    except Exception as e:
        logger.error(f"Unexpected error in get_google_integration: {e}")
        return JSONResponse(
            content=error_response(
                message="An unexpected error occurred",
                code="server_error"
            ),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.post("/")
async def create_google_integration(
    item_data: GoogleIntegrationCreate,
    db: Session = Depends(get_db)
):
    """Create a new Google integration with standardized response format"""
    try:
        # Call the original handler
        new_item = await original_create(item_data=item_data, db=db)
        
        return JSONResponse(
            content=success_response(
                data=new_item.dict(),
                message="Google integration created successfully"
            ),
            status_code=status.HTTP_201_CREATED
        )
    except HTTPException as e:
        return JSONResponse(
            content=error_response(
                message=e.detail,
                code="database_error"
            ),
            status_code=e.status_code
        )
    except Exception as e:
        logger.error(f"Unexpected error in create_google_integration: {e}")
        return JSONResponse(
            content=error_response(
                message="An unexpected error occurred",
                code="server_error"
            ),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.put("/{integration_id}")
async def update_google_integration(
    integration_id: str,
    item_update: GoogleIntegrationUpdate,
    db: Session = Depends(get_db)
):
    """Update an existing Google integration with standardized response format"""
    try:
        # Call the original handler
        updated_item = await original_update(
            integration_id=integration_id,
            item_update=item_update,
            db=db
        )
        
        return JSONResponse(
            content=success_response(
                data=updated_item.dict(),
                message="Google integration updated successfully"
            )
        )
    except HTTPException as e:
        return JSONResponse(
            content=error_response(
                message=e.detail,
                code="not_found" if e.status_code == status.HTTP_404_NOT_FOUND else "database_error"
            ),
            status_code=e.status_code
        )
    except Exception as e:
        logger.error(f"Unexpected error in update_google_integration: {e}")
        return JSONResponse(
            content=error_response(
                message="An unexpected error occurred",
                code="server_error"
            ),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.delete("/{integration_id}")
async def delete_google_integration(
    integration_id: str,
    db: Session = Depends(get_db)
):
    """Delete a Google integration with standardized response format"""
    try:
        # Call the original handler
        await original_delete(integration_id=integration_id, db=db)
        
        return JSONResponse(
            content=success_response(
                message="Google integration deleted successfully"
            ),
            status_code=status.HTTP_200_OK
        )
    except HTTPException as e:
        return JSONResponse(
            content=error_response(
                message=e.detail,
                code="not_found" if e.status_code == status.HTTP_404_NOT_FOUND else "database_error"
            ),
            status_code=e.status_code
        )
    except Exception as e:
        logger.error(f"Unexpected error in delete_google_integration: {e}")
        return JSONResponse(
            content=error_response(
                message="An unexpected error occurred",
                code="server_error"
            ),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@router.get("/status")
async def get_integration_status(request: Request, db: AsyncSession = Depends(get_db)):
    """Get the status of the user's Google integration."""
    try:
        # Check if user is logged in
        if "user" not in request.session:
            raise HTTPException(status_code=401, detail="Not authenticated")

        user = request.session["user"]
        user_id = user.get("id")

        # Get integration status from database
        query = select(GoogleIntegration).where(
            GoogleIntegration.user_id == user_id,
            GoogleIntegration.is_active == True
        )
        result = await db.execute(query)
        integration = result.scalar_one_or_none()

        if not integration:
            raise HTTPException(status_code=404, detail="Google integration not found")

        return {
            "id": integration.id,
            "email": integration.email,
            "is_active": integration.is_active,
            "status": integration.status,
            "created_at": integration.created_at.isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in get_google_integration: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/disconnect")
async def disconnect_integration(request: Request, db: Session = Depends(get_db)):
    """Disconnect Google integration."""
    try:
        # Get user from session
        user = request.session.get("user")
        if not user:
            raise HTTPException(status_code=401, detail="Not logged in")

        # Find active integration using async syntax
        result = await db.execute(
            select(GoogleIntegration).where(
                GoogleIntegration.email == user.get("email"),
                GoogleIntegration.status == "connected"
            )
        )
        integration = result.scalar_one_or_none()

        if not integration:
            raise HTTPException(status_code=404, detail="No active Google integration found")

        # Update integration status
        integration.status = "disconnected"
        await db.commit()

        return JSONResponse({
            "success": True,
            "message": "Successfully disconnected Google integration"
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error disconnecting Google integration: {e}")
        raise HTTPException(status_code=500, detail=str(e))
