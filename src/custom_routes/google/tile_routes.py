"""Routes for Google Tiles functionality.

This module handles routes for fetching and displaying tiles
created from a user's Google/Gmail data.
"""
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import List, Dict, Any, Optional
import os
import logging
from datetime import datetime, timedelta
import re
import json

from src.config.integration_config import IntegrationConfig
from src.config.adapter_factory import AdapterFactory
from src.services.transformation_service import TransformationService
from ...custom_schemas.google_schemas import Tile, RelatedEvent, TileResponse

# Configure templates and router
templates = Jinja2Templates(directory="templates")
router = APIRouter(prefix="/google-tiles", tags=["google-tiles"])

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_google_credentials(request: Request) -> Dict[str, Any]:
    """Get Google credentials from session.
    
    Args:
        request: FastAPI request object
        
    Returns:
        Dict[str, Any]: Google credentials
        
    Raises:
        HTTPException: If user is not logged in or Google not connected
    """
    # Check if user is logged in
    if "user_id" not in request.session:
        raise HTTPException(status_code=401, detail="Not logged in")
    
    # Get user's Google credentials
    user_id = request.session["user_id"]
    # This would normally pull from a database, but we'll use our config system
    config = IntegrationConfig()
    credentials = config.get_credentials("gmail")
    
    if not credentials:
        raise HTTPException(status_code=401, detail="Google account not connected")
    
    return credentials


def fetch_and_transform_emails(credentials: Dict[str, Any], limit: int = 10) -> List[Any]:
    """Fetch emails and transform them into tiles.
    
    Args:
        credentials: Google credentials
        limit: Maximum number of emails to fetch
        
    Returns:
        List[Any]: List of tile objects
    """
    # Create adapter factory and get Gmail adapter
    factory = AdapterFactory()
    gmail_adapter = factory.create_adapter("gmail")
    
    if not gmail_adapter:
        logger.error("Failed to create Gmail adapter")
        return []
    
    # Connect to Gmail
    connected = gmail_adapter.connect(credentials)
    if not connected:
        logger.error("Failed to connect to Gmail")
        return []
    
    try:
        # Fetch emails
        emails = gmail_adapter.fetch_data(limit=limit)
        logger.info(f"Fetched {len(emails)} emails")
        
        # Transform emails to tiles
        transformation_service = TransformationService()
        tiles = transformation_service.transform_to_tiles(emails, 'email')
        logger.info(f"Transformed {len(tiles)} emails into tiles")
        
        return tiles
    finally:
        # Disconnect adapter
        gmail_adapter.disconnect()


@router.get("/view", response_class=HTMLResponse)
async def view_google_tiles(
    request: Request, 
    limit: int = 10
):
    """View tiles generated from Google data.
    
    Args:
        request: FastAPI request
        limit: Maximum number of emails/tiles to fetch
        
    Returns:
        HTMLResponse: Rendered HTML template with tiles
    """
    try:
        # Get credentials
        credentials = get_google_credentials(request)
        
        # Fetch and transform emails
        tiles = fetch_and_transform_emails(credentials, limit)
        
        # Render template
        return templates.TemplateResponse(
            "google_tiles.html",
            {
                "request": request,
                "tiles": tiles,
                "count": len(tiles),
                "title": "Your Gmail Tiles"
            }
        )
    except HTTPException as e:
        # Redirect to connect page if not authenticated
        if e.status_code == 401:
            return templates.TemplateResponse(
                "google_connect.html",
                {
                    "request": request,
                    "connection_status": {"is_connected": False},
                    "google_client_id": credentials.get("client_id", "") if "credentials" in locals() else "",
                    "error_message": e.detail
                }
            )
        raise
    except Exception as e:
        logger.error(f"Error in view_google_tiles: {e}")
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "error_message": f"Failed to load tiles: {str(e)}"
            }
        )


@router.get("/api/tiles")
async def api_google_tiles(
    request: Request,
    limit: int = 10
):
    """API endpoint for fetching Google tiles as JSON.
    
    Args:
        request: FastAPI request
        limit: Maximum number of emails/tiles to fetch
        
    Returns:
        Dict: JSON response with tiles data
    """
    try:
        # Get credentials
        credentials = get_google_credentials(request)
        
        # Fetch and transform emails
        tiles = fetch_and_transform_emails(credentials, limit)
        
        # We need to convert Tile objects to dictionaries
        tiles_dict = [tile.dict() for tile in tiles]
        
        return {
            "success": True,
            "count": len(tiles),
            "tiles": tiles_dict
        }
    except HTTPException as e:
        return {
            "success": False,
            "error": e.detail
        }
    except Exception as e:
        logger.error(f"Error in api_google_tiles: {e}")
        return {
            "success": False,
            "error": f"Failed to load tiles: {str(e)}"
        } 