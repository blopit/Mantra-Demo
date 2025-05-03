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
