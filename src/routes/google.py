"""
FastAPI router for Google authentication endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import os
import logging
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
import uuid
from sqlalchemy.exc import SQLAlchemyError
from uuid import UUID

from ..dependencies import get_db
from ..models.users import Users
from ..models import GoogleIntegration, LayoutTabs, Tiles, TileMetadata
from ..services.google_auth import GoogleAuthService
from ..schemas.users import UsersCreate
from src.providers.google import GoogleAuthManager, GmailService, GoogleCredentialsManager

# Initialize services
gmail_service = GmailService()  # Initialize Gmail service
from src.custom_routes.google.service_routes import get_current_user, UserResponse

# Pydantic models for responses
class AuthUrlResponse(BaseModel):
    auth_url: str

class FeedTab(BaseModel):
    id: str
    name: str
    tab_id: str
    icon: str
    order: int
    has_scope: bool

class FeedTabsResponse(BaseModel):
    feed_tabs: List[FeedTab]

class GoogleStatusResponse(BaseModel):
    status: str
    email: Optional[str] = None

class GmailTile(BaseModel):
    id: str
    title: str
    content: str
    category: str
    created_at: Optional[str] = None
    actions: List[Dict[str, str]] = Field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = None

class GmailTilesResponse(BaseModel):
    tiles: List[GmailTile]

class StatusResponse(BaseModel):
    status: str

class TileResponse(BaseModel):
    id: str
    title: str
    content: str
    category: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    is_focus: bool = False
    is_ai_curated: bool = False
    metadata: Optional[Dict[str, Any]] = None
    actions: List[Dict[str, str]] = Field(default_factory=list)

class UnsubscribeRequest(BaseModel):
    message_id: str

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/google", tags=["Google Integration"])

# Initialize services
auth_manager = GoogleAuthManager()
gmail_service = GmailService()
credentials_manager = GoogleCredentialsManager()

@router.get("/auth", response_model=AuthUrlResponse)
async def google_auth(redirect_url: str = "/", user: UserResponse = Depends(get_current_user)):
    """Generate Google OAuth URL"""
    logger.info(f"Generating auth URL for user {user.id} with redirect URL: {redirect_url}")
    auth_service = GoogleAuthService()

    # Construct the full callback URL
    callback_url = "http://localhost:8000/api/google/callback"

    # Get authorization URL with proper parameters
    auth_url = auth_service.get_authorization_url(
        redirect_url=callback_url,
        user_id=str(user.id)
    )
    return {"auth_url": auth_url}

@router.get("/refresh-auth")
async def refresh_google_auth(
    request: Request,
    return_url: str = "/",
    user: UserResponse = Depends(get_current_user)
):
    """
    Redirect to Google OAuth flow to refresh credentials
    """
    logger.info(f"Initiating auth refresh for user {user.id}")

    # Clear existing credentials
    await credentials_manager.clear_credentials(str(user.id))

    # Generate new auth URL
    auth_service = GoogleAuthService()
    callback_url = "http://localhost:8000/api/google/callback"

    # Get authorization URL with proper parameters and return URL
    auth_url = auth_service.get_authorization_url(
        redirect_url=callback_url,
        user_id=str(user.id),
        state=return_url  # Pass return URL in state
    )

    return RedirectResponse(url=auth_url)

@router.get("/feed-tabs", response_model=FeedTabsResponse)
async def get_feed_tabs(request: Request, db: Session = Depends(get_db)):
    """Get available feed tabs for the authenticated user"""
    try:
        # Get user ID from session
        user_id = request.session.get("user_id")
        if not user_id:
            logger.warning("No user_id found in session")
            raise HTTPException(status_code=401, detail="User not authenticated")

        # Get user's Google integration
        integration = db.query(GoogleIntegration).filter(
            GoogleIntegration.user_id == user_id,
            GoogleIntegration.status == "active"
        ).first()

        if not integration:
            logger.info(f"No active Google integration found for user {user_id}")
            return {"feed_tabs": []}

        # Get layout tabs that correspond to Google feed types
        layout_tabs = db.query(LayoutTabs).filter(
            LayoutTabs.name.in_(["gmail", "calendar", "todo", "social"])
        ).order_by(LayoutTabs.order).all()

        # If no tabs exist, create default ones
        if not layout_tabs:
            default_tabs = [
                {
                    "name": "gmail",
                    "tab_id": "gmail",
                    "icon": "email",
                    "order": 0,
                    "is_default": True,
                    "user_id": user_id
                },
                {
                    "name": "calendar",
                    "tab_id": "calendar",
                    "icon": "calendar_today",
                    "order": 1,
                    "is_default": False,
                    "user_id": user_id
                },
                {
                    "name": "todo",
                    "tab_id": "todo",
                    "icon": "check_circle",
                    "order": 2,
                    "is_default": False,
                    "user_id": user_id
                },
                {
                    "name": "social",
                    "tab_id": "social",
                    "icon": "people",
                    "order": 3,
                    "is_default": False,
                    "user_id": user_id
                }
            ]

            for tab_data in default_tabs:
                new_tab = LayoutTabs(
                    id=str(uuid.uuid4()),
                    name=tab_data["name"],
                    tab_id=tab_data["tab_id"],
                    icon=tab_data["icon"],
                    order=tab_data["order"],
                    is_default=tab_data["is_default"],
                    user_id=tab_data["user_id"]
                )
                db.add(new_tab)
                layout_tabs.append(new_tab)

            try:
                db.commit()
            except SQLAlchemyError as e:
                logger.error(f"Failed to create default tabs: {e}")
                db.rollback()

        # Format tab info
        feed_tabs = []
        for tab in layout_tabs:
            # Handle scopes whether it's a string or list
            scopes = integration.scopes
            scopes_str = scopes if isinstance(scopes, str) else ",".join(scopes) if isinstance(scopes, list) else ""
            scopes_str = scopes_str.lower()

            has_scope = (
                tab.name.lower() in scopes_str or  # Direct scope match
                (tab.name.lower() == "gmail" and "gmail.readonly" in scopes_str) or  # Gmail special case
                (tab.name.lower() == "calendar" and "calendar.readonly" in scopes_str)  # Calendar special case
            )

            feed_tabs.append({
                "id": str(tab.id),  # Convert UUID to string
                "name": tab.name,
                "tab_id": tab.tab_id,
                "icon": tab.icon,
                "order": tab.order,
                "has_scope": has_scope
            })

        logger.info(f"Returning {len(feed_tabs)} feed tabs for user {user_id}")
        return {"feed_tabs": feed_tabs}
    except Exception as e:
        logger.error(f"Error fetching feed tabs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/login")
async def google_login(request: Request):
    """Initiate Google OAuth login flow"""
    auth_service = GoogleAuthService()
    authorization_url = auth_service.get_authorization_url(
        redirect_url=str(request.base_url) + "api/google/callback"
    )
    return RedirectResponse(url=authorization_url)

@router.get("/callback")
async def google_callback(state: str, code: str, request: Request, db: Session = Depends(get_db)):
    """Handle Google OAuth callback"""
    try:
        auth_service = GoogleAuthService()

        # Get user from state (user ID)
        try:
            user_id = UUID(state)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid state parameter")

        # Get the callback URL
        callback_url = str(request.base_url) + "api/google/callback"

        # Handle OAuth callback
        user_info, credentials = await auth_service.handle_callback(
            code=code,
            redirect_uri=callback_url
        )

        logger.info(f"Attempting to create/update Google integration for user {user_id}")

        # Get or create integration
        integration = db.query(GoogleIntegration).filter(
            GoogleIntegration.user_id == str(user_id)
        ).first()

        if integration:
            logger.info("Updating existing Google integration")
            integration.access_token = credentials.token
            integration.refresh_token = credentials.refresh_token
            integration.token_expiry = credentials.expiry
            integration.email = user_info["email"]
            integration.scopes = credentials.scopes
            integration.status = "active"
        else:
            logger.info("Creating new Google integration")
            integration = GoogleIntegration(
                user_id=str(user_id),
                email=user_info["email"],
                access_token=credentials.token,
                refresh_token=credentials.refresh_token,
                token_expiry=credentials.expiry,
                scopes=credentials.scopes,
                status="active"
            )
            db.add(integration)

        try:
            db.commit()
            logger.info(f"Successfully created/updated Google integration for user: {user_info['email']}")
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Database error while saving integration: {e}")
            raise HTTPException(status_code=500, detail="Failed to save integration")

        # Redirect to frontend
        redirect_url = request.query_params.get("redirect_url", "/")
        return RedirectResponse(url=redirect_url)

    except Exception as e:
        logger.error(f"Error in Google callback: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status", response_model=GoogleStatusResponse)
async def get_google_status(user: UserResponse = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get Google integration status"""
    try:
        integration = db.query(GoogleIntegration).filter(
            GoogleIntegration.user_id == user.id,
            GoogleIntegration.status == "active"
        ).first()

        if not integration:
            return {"status": "not_connected"}

        return {
            "status": "connected",
            "email": integration.email
        }

    except Exception as e:
        logger.error(f"Error getting Google status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/feed-tiles")
async def get_feed_tiles(
    feed_type: str,
    force_refresh: bool = False,
    user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get feed tiles for the specified feed type"""
    try:
        # Get user's Google integration
        integration = db.query(GoogleIntegration).filter(
            GoogleIntegration.user_id == str(user.id),
            GoogleIntegration.status == "active"
        ).first()

        if not integration:
            logger.warning(f"No active Google integration found for user {user.id}")
            return {"tiles": []}

        # Initialize appropriate service based on feed type
        if feed_type == "gmail":
            try:
                # Construct credentials dictionary
                credentials = {
                    "access_token": integration.access_token,
                    "refresh_token": integration.refresh_token,
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "client_id": os.getenv("GOOGLE_CLIENT_ID"),
                    "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
                    "scopes": integration.scopes.split(",") if isinstance(integration.scopes, str) else integration.scopes,
                    "user_id": str(user.id)  # Add user_id for error handling
                }

                # Connect to Gmail service
                connection_result = await gmail_service.connect(credentials)
                if not connection_result:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Failed to connect to Gmail API"
                    )

                # Get messages and process them into tiles
                messages = await gmail_service.get_messages(max_results=20)
                tiles = []

                for msg in messages:
                    # Process message into tile format
                    processed = gmail_service._process_message(msg)
                    if processed:
                        tiles.append(processed)

                return {"tiles": tiles}

            except HTTPException as he:
                # If it's our auth error, propagate it
                if he.status_code == 401 and "X-Redirect" in he.headers:
                    raise he
                logger.error(f"HTTP error in Gmail service: {he}")
                return {"tiles": [], "error": str(he)}

            except Exception as e:
                logger.error(f"Error getting Gmail tiles: {e}")
                return {"tiles": [], "error": "Failed to fetch Gmail data"}

        # Handle other feed types...
        return {"tiles": []}

    except HTTPException as he:
        # Propagate auth errors with redirect
        if he.status_code == 401 and "X-Redirect" in he.headers:
            raise he
        logger.error(f"HTTP error in feed tiles: {he}")
        return {"tiles": [], "error": str(he)}

    except Exception as e:
        logger.error(f"Error getting feed tiles: {e}")
        return {"tiles": [], "error": "Failed to fetch feed data"}

@router.delete("/disconnect", response_model=StatusResponse)
async def disconnect_google(user: UserResponse = Depends(get_current_user), db: Session = Depends(get_db)):
    """Disconnect Google integration"""
    try:
        integration = db.query(GoogleIntegration).filter(
            GoogleIntegration.user_id == user.id,
            GoogleIntegration.status == "active"
        ).first()

        if integration:
            integration.status = "disconnected"
            db.commit()

        return {"status": "success"}

    except Exception as e:
        logger.error(f"Error disconnecting Google integration: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tiles/{tile_id}")
async def get_tile_details(
    tile_id: str,
    user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get details for a specific tile

    Args:
        tile_id: ID of the tile (Gmail message ID)
        user: Current authenticated user
        db: Database session
    """
    logger.info(f"Fetching details for tile {tile_id} for user {user.id}")

    try:
        # Check for active Google integration
        integration = db.query(GoogleIntegration).filter(
            GoogleIntegration.user_id == UUID(user.id),
            GoogleIntegration.status == "active"
        ).first()

        if not integration:
            logger.warning(f"No active Google integration found for user {user.id}")
            raise HTTPException(status_code=404, detail="No active Google integration found")

        # Build credentials dictionary
        credentials = {
            "access_token": integration.access_token,
            "refresh_token": integration.refresh_token,
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": os.getenv("GOOGLE_CLIENT_ID", ""),
            "client_secret": os.getenv("GOOGLE_CLIENT_SECRET", ""),
            "scopes": integration.scopes.split(",") if isinstance(integration.scopes, str) else integration.scopes
        }

        # Validate and refresh token if needed
        if not auth_manager.validate_and_refresh(credentials):
            logger.error(f"Invalid or expired credentials for user {user.id}")
            raise HTTPException(status_code=401, detail="Invalid or expired credentials")

        # Connect to Gmail service
        if not await gmail_service.connect(credentials):
            logger.error(f"Failed to connect to Gmail API for user {user.id}")
            raise HTTPException(status_code=500, detail="Failed to connect to Gmail API")

        # Get message details
        message = await gmail_service.get_message(tile_id)
        if not message:
            logger.warning(f"Message {tile_id} not found")
            raise HTTPException(status_code=404, detail="Message not found")

        # Extract headers
        headers = message.get("payload", {}).get("headers", [])
        subject = next((h["value"] for h in headers if h["name"].lower() == "subject"), "No Subject")
        date = next((h["value"] for h in headers if h["name"].lower() == "date"), None)
        from_header = next((h["value"] for h in headers if h["name"].lower() == "from"), None)

        # Parse from header
        metadata = {}
        if from_header:
            # Basic parsing of "Name <email@domain.com>" format
            if "<" in from_header and ">" in from_header:
                name = from_header[:from_header.find("<")].strip()
                email = from_header[from_header.find("<")+1:from_header.find(">")]
                metadata["from"] = {"name": name, "email": email}
            else:
                metadata["from"] = {"name": from_header, "email": None}

        # Add platform specific data
        metadata["platform_specific_data"] = {
            "message_id": message.get("id"),
            "thread_id": message.get("threadId"),
            "label_ids": message.get("labelIds", [])
        }

        # Create response
        response = {
            "id": message.get("id"),
            "title": subject,
            "content": message.get("snippet", ""),
            "category": "gmail",
            "created_at": date,
            "updated_at": date,  # For emails, created and updated are the same
            "is_focus": "IMPORTANT" in message.get("labelIds", []),
            "is_ai_curated": False,  # Future feature
            "metadata": metadata,
            "actions": [
                {
                    "action_type": "view",
                    "label": "View Email",
                    "url": f"https://mail.google.com/mail/u/0/#inbox/{message.get('id')}"
                }
            ]
        }

        logger.info(f"Successfully fetched details for tile {tile_id}")
        return response

    except Exception as e:
        logger.error(f"Error getting tile details for {tile_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/unsubscribe")
async def handle_unsubscribe(
    request: UnsubscribeRequest,
    user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Handle unsubscribe request for an email

    Args:
        request: UnsubscribeRequest containing message_id
        user: Current authenticated user
        db: Database session
    """
    logger.info(f"Processing unsubscribe request for message {request.message_id} from user {user.id}")

    try:
        # Check for active Google integration
        integration = db.query(GoogleIntegration).filter(
            GoogleIntegration.user_id == UUID(user.id),
            GoogleIntegration.status == "active"
        ).first()

        if not integration:
            logger.warning(f"No active Google integration found for user {user.id}")
            raise HTTPException(status_code=404, detail="No active Google integration found")

        # Build credentials dictionary
        credentials = {
            "access_token": integration.access_token,
            "refresh_token": integration.refresh_token,
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": os.getenv("GOOGLE_CLIENT_ID", ""),
            "client_secret": os.getenv("GOOGLE_CLIENT_SECRET", ""),
            "scopes": integration.scopes.split(",") if isinstance(integration.scopes, str) else integration.scopes
        }

        # Validate and refresh token if needed
        if not auth_manager.validate_and_refresh(credentials):
            logger.error(f"Invalid or expired credentials for user {user.id}")
            raise HTTPException(status_code=401, detail="Invalid or expired credentials")

        # Connect to Gmail service
        if not await gmail_service.connect(credentials):
            logger.error(f"Failed to connect to Gmail API for user {user.id}")
            raise HTTPException(status_code=500, detail="Failed to connect to Gmail API")

        # Get message details to extract unsubscribe info
        message = await gmail_service.get_message(request.message_id)
        if not message:
            logger.warning(f"Message {request.message_id} not found")
            raise HTTPException(status_code=404, detail="Message not found")

        # Extract List-Unsubscribe header
        headers = message.get("payload", {}).get("headers", [])
        list_unsubscribe = next((h["value"] for h in headers if h["name"].lower() == "list-unsubscribe"), None)

        if not list_unsubscribe:
            logger.warning(f"No List-Unsubscribe header found in message {request.message_id}")
            raise HTTPException(status_code=404, detail="No unsubscribe link found")

        # Parse unsubscribe URLs
        urls = []
        if "<" in list_unsubscribe and ">" in list_unsubscribe:
            urls = [url.strip(" <>") for url in list_unsubscribe.split(",")]
        else:
            urls = [list_unsubscribe.strip()]

        # Find the best unsubscribe method
        unsubscribe_url = None
        mailto_url = None

        for url in urls:
            if url.lower().startswith("http"):
                unsubscribe_url = url
                break
            elif url.lower().startswith("mailto:"):
                mailto_url = url

        # Prefer HTTP(S) URL over mailto
        final_url = unsubscribe_url or mailto_url

        if not final_url:
            logger.warning(f"No valid unsubscribe URL found in message {request.message_id}")
            raise HTTPException(status_code=404, detail="No valid unsubscribe link found")

        # Return the appropriate response based on URL type
        if final_url.lower().startswith("mailto:"):
            return {
                "type": "mailto",
                "url": final_url
            }
        else:
            # For HTTP(S) URLs, we'll return both GET and POST URLs
            # The frontend can try GET first, then fall back to POST if needed
            return {
                "type": "http",
                "url": final_url,
                "methods": ["GET", "POST"]
            }

    except Exception as e:
        logger.error(f"Error processing unsubscribe request: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))