"""
Consolidated Google routes for Ultimate Assistant.
Handles Google OAuth2 flow, API integration, and fetching Gmail data.
"""

import os
import logging
import time
import uuid
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, Depends, Request, Response, HTTPException, status, Query
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from starlette.middleware.sessions import SessionMiddleware
from datetime import datetime, timedelta, timezone
from uuid import uuid4, UUID
from types import SimpleNamespace
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.dialects.postgresql import UUID as SQLUUID
from sqlalchemy import text

from src.utils.database import get_db
from src.models.google_integration import GoogleIntegration
from src.models.layout_tabs import LayoutTabs
from src.models.users import Users
from src.models.tiles import Tiles
from src.models.section_tiles import SectionTiles
from src.models.layout_sections import LayoutSections
from src.services.transformation_service import TransformationService
from src.providers.google import GoogleAuthManager, GmailService, GoogleCredentialsManager
from src.models.tile_metadata import TileMetadata
from src.schemas.tile_metadata import PlatformSpecificData
from src.dependencies import get_db
from src.services.google_auth import GoogleAuthService
from src.models.base import GUID
import traceback

router = APIRouter(prefix="/api/google", tags=["google"])
logger = logging.getLogger(__name__)

# Pydantic models
class UserResponse(BaseModel):
    id: str
    email: Optional[str] = None

# Initialize services
def get_auth_manager(db: Session = Depends(get_db)) -> GoogleAuthManager:
    return GoogleAuthManager(db)

def get_gmail_service(db: Session = Depends(get_db)) -> GmailService:
    return GmailService(db)

transformation_service = TransformationService()
credentials_manager = GoogleCredentialsManager()

async def get_current_user(request: Request, db: Session = Depends(get_db)) -> Optional[UserResponse]:
    """Get the current user from the session or active integration"""
    user_id = request.session.get("user_id")

    if not user_id and db:
        # Check if we have any active integrations
        integration = db.query(GoogleIntegration).filter(
            GoogleIntegration.status == 'active'
        ).order_by(GoogleIntegration.created_at.desc()).first()

        if integration:
            user_id = str(integration.user_id)
            request.session["user_id"] = user_id
            logger.info(f"Found active integration for user: {user_id}")

            return UserResponse(
                id=user_id,
                email=integration.email
            )

    if user_id:
        return UserResponse(
            id=user_id,
            email=request.session.get("user_email", "")
        )

    return None

async def get_gmail_tiles(
    user: UserResponse,
    limit: int,
    force_refresh: bool,
    db: Session,
    auth_manager: GoogleAuthManager = Depends(get_auth_manager)
) -> List[Tiles]:
    """Get Gmail tiles for a user"""
    try:
        # Convert user_id to UUID if it's a string
        try:
            user_uuid = UUID(user.id) if isinstance(user.id, str) else user.id
        except ValueError as e:
            logger.error(f"Invalid UUID format for user_id: {user.id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid UUID format: {str(e)}"
            )

        # Get Google integration for this user
        integration = db.query(GoogleIntegration).filter(
            GoogleIntegration.user_id == user_uuid,
            GoogleIntegration.status == "active"
        ).first()

        if not integration:
            logger.error(f"No active Google integration found for user {user_uuid}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active Google integration found"
            )

        # Get existing tiles for this user
        existing_tiles = db.query(Tiles).filter(
            Tiles.user_id == user_uuid,
            Tiles.category == "gmail"
        ).all()

        # Initialize variables
        should_fetch = force_refresh or not existing_tiles
        valid_timestamps = False
        current_time = datetime.now(timezone.utc)

        if not should_fetch and existing_tiles:
            # Check if we have valid timestamps and if cache has expired
            valid_timestamps = all(tile.created_at is not None for tile in existing_tiles)
            if valid_timestamps:
                # Get the most recent tile's timestamp
                most_recent = max(tile.created_at for tile in existing_tiles)
                cache_expires_at = most_recent + timedelta(minutes=5)  # 5-minute cache

                # Fetch if cache has expired or we don't have enough tiles
                should_fetch = current_time > cache_expires_at or len(existing_tiles) < limit

        # Initialize list for all tiles
        all_tiles = []

        if should_fetch:
            logger.info(f"Fetching new email data (reason: {'no_valid_timestamps' if not valid_timestamps else 'cache_expired' if current_time > cache_expires_at else 'force_refresh' if force_refresh else 'insufficient_tiles'})")

            # Build credentials dictionary from stored integration
            credentials = {
                "access_token": integration.access_token,
                "refresh_token": integration.refresh_token,
                "token_uri": "https://oauth2.googleapis.com/token",
                "client_id": os.getenv("GOOGLE_CLIENT_ID", ""),
                "client_secret": os.getenv("GOOGLE_CLIENT_SECRET", ""),
                "scopes": integration.scopes.split(",") if isinstance(integration.scopes, str) else integration.scopes,
                "expiry": int(integration.token_expiry.timestamp()) if integration.token_expiry else None
            }

            # Validate and refresh token if needed
            token_valid = auth_manager.validate_and_refresh(credentials)

            if not token_valid:
                logger.error("Token validation failed")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired credentials"
                )

            # Connect to Gmail service
            connection_result = get_gmail_service(db).connect(credentials)

            if not connection_result:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to connect to Gmail API"
                )

            # Fetch emails
            emails = get_gmail_service(db).get_messages(max_results=limit)

            if not emails:
                logger.info("No emails retrieved from Gmail API")
                return []

            # Transform emails to tiles
            transformed_tiles = transformation_service.transform_to_tiles(emails, 'email', user_uuid)
            logger.info(f"Transformed {len(transformed_tiles)} emails to tiles")

            # Store the tiles in the database
            for tile_data in transformed_tiles:
                try:
                    # Generate a new UUID for the tile
                    tile_id = uuid4()
                    logger.info(f"Creating new tile with ID: {tile_id}")

                    # Create new tile with proper UUID handling
                    new_tile = Tiles(
                        id=tile_id,  # Use UUID directly
                        user_id=user_uuid,  # Use UUID directly
                        title=tile_data.title,
                        content=tile_data.content,
                        category="gmail",
                        created_at=current_time,
                        updated_at=current_time,
                        is_focus=tile_data.is_focus,
                        is_ai_curated=tile_data.is_ai_curated
                    )
                    logger.info(f"Created Tiles object with title: {tile_data.title[:50]}...")

                    # Get platform-specific data from tile_data's metadata
                    platform_data = {}
                    if hasattr(tile_data, 'tile_metadata') and tile_data.tile_metadata:
                        platform_data = tile_data.tile_metadata.platform_specific_data or {}

                    # Create tile metadata
                    metadata = TileMetadata(
                        id=uuid4(),  # Generate new UUID for metadata
                        tile_id=tile_id,  # Use the same tile_id
                        source="gmail",
                        message_id=tile_data.id,  # Original message ID from Gmail
                        platform_specific_data=platform_data  # Use the platform-specific data from tile_data
                    )
                    logger.info(f"Created TileMetadata object for message ID: {tile_data.id}")

                    # Add to database and flush to ensure IDs are generated
                    db.add(new_tile)
                    db.add(metadata)
                    logger.info("Added tile and metadata to session")

                    try:
                        db.flush()
                        logger.info("Successfully flushed tile and metadata to database")
                        all_tiles.append(new_tile)
                    except SQLAlchemyError as flush_error:
                        logger.error(f"Error flushing tile to database: {str(flush_error)}")
                        db.rollback()
                        continue

                except SQLAlchemyError as e:
                    logger.error(f"SQLAlchemy error creating tile: {str(e)}")
                    db.rollback()
                    continue
                except Exception as e:
                    logger.error(f"Unexpected error creating tile: {str(e)}")
                    logger.error(f"Tile data: {tile_data}")
                    db.rollback()
                    continue

            try:
                # Commit all changes
                logger.info(f"Attempting to commit {len(all_tiles)} tiles")
                db.commit()
                logger.info(f"Successfully committed {len(all_tiles)} new tiles")
            except SQLAlchemyError as e:
                logger.error(f"Error committing tiles: {str(e)}")
                logger.error("Rolling back transaction")
                db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to save tiles"
                )

        return all_tiles

    except Exception as e:
        logger.error(f"Error in get_gmail_tiles: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting Gmail tiles: {str(e)}"
        )

REQUIRED_SCOPES = [
    'https://www.googleapis.com/auth/userinfo.profile',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/calendar.readonly',
    'https://www.googleapis.com/auth/tasks.readonly',
    'openid'
]

@router.get("/auth")
async def google_auth(
    request: Request,
    redirect_url: str = "/",
    auth_manager: GoogleAuthManager = Depends(get_auth_manager)
):
    """Start Google OAuth flow"""
    try:
        # Generate state token and store in session
        state = str(uuid4())
        request.session["oauth_state"] = state
        request.session["redirect_url"] = redirect_url

        # Get the authorization URL
        redirect_uri = str(request.base_url) + "callback"
        auth_url = auth_manager.get_authorization_url(
            redirect_uri=redirect_uri,
            state=state
        )

        return RedirectResponse(url=auth_url)
    except Exception as e:
        logger.error(f"Error starting OAuth flow: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/callback")
async def google_callback(
    request: Request,
    code: str = None,
    error: str = None,
    db: Session = Depends(get_db),
    auth_manager: GoogleAuthManager = Depends(get_auth_manager)
):
    """Handle Google OAuth callback"""
    try:
        # Check for errors
        if error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"OAuth error: {error}"
            )

        # Get stored state and redirect URL
        stored_state = request.session.get("oauth_state")
        redirect_url = request.session.get("redirect_url", "/")

        # Exchange code for credentials
        redirect_uri = str(request.base_url)
        credentials = auth_manager.exchange_code(code, redirect_uri)

        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to exchange code for credentials"
            )

        # Get user info
        user_info = auth_manager.get_user_info(credentials)
        if not user_info:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get user info"
            )

        # Get the user ID either from session or use hardcoded ID
        user_id = request.session.get("user_id")
        if not user_id:
            # Use hardcoded user ID for now
            # TODO: Implement proper authentication
            user_id = "52cb4d8f-ca71-484b-9228-112070c4947a"
            request.session["user_id"] = user_id

            # Check if user exists in database
            user = db.query(Users).filter(Users.id == user_id).first()
            if not user:
                # Create user if not exists
                logger.info(f"Creating user with ID: {user_id}")
                try:
                    # Generate a unique username from email
                    email = user_info.get('email', '')
                    username = f"user_{email.split('@')[0]}"

                    # Create user with all required fields
                    demo_user = Users(
                        id=UUID(user_id),  # Convert string to UUID
                        username=username,  # Use processed username
                        email=email,  # Use actual Google email
                        password_hash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewKyNiAYMxRHHJ8m",  # Dummy hash for OAuth users
                        is_active=True,
                        first_name=user_info.get('given_name', ''),
                        last_name=user_info.get('family_name', '')
                    )
                    db.add(demo_user)
                    db.commit()
                    logger.info(f"Created user with ID: {user_id}")
                except Exception as e:
                    db.rollback()
                    logger.error(f"Failed to create user: {e}")
                    return RedirectResponse(url=f"{redirect_url}?error=failed_to_create_user&message={str(e)}")

        # Store in database for persistence
        try:
            # Check if integration already exists
            google_integration = db.query(GoogleIntegration).filter(
                GoogleIntegration.user_id == user_id,
                GoogleIntegration.email == user_info.get("email")
            ).first()

            expires_at = datetime.fromtimestamp(int(time.time()) + 3600)  # Default 1 hour
            if "expiry" in credentials:
                expires_at = datetime.fromtimestamp(credentials["expiry"])

            if google_integration:
                # Update existing integration
                google_integration.access_token = credentials.get("access_token", "")
                if credentials.get("refresh_token"):  # Only update if provided
                    google_integration.refresh_token = credentials.get("refresh_token")
                google_integration.token_expiry = expires_at

                # Store scopes appropriately in the JSON column
                scopes = credentials.get("scopes", [])
                google_integration.scopes = scopes  # JSON column will store the list directly
                google_integration.status = "active"

                # If we didn't have the Google account ID before, add it now
                if not google_integration.google_account_id and "id" in user_info:
                    google_integration.google_account_id = user_info["id"]
            else:
                # Create new integration
                google_integration = GoogleIntegration(
                    user_id=user_id,
                    google_account_id=user_info.get("id", f"google_{user_info.get('email')}"),
                    email=user_info.get("email"),
                    access_token=credentials.get("access_token", ""),
                    refresh_token=credentials.get("refresh_token", ""),
                    token_expiry=expires_at,
                    scopes=scopes,
                    status="active"
                )
                db.add(google_integration)

            db.commit()
            logger.info(f"Saved Google integration for user {user_id} with email {user_info.get('email')}")

            # Store minimal info in session for client-side awareness
            request.session["is_connected"] = True
            request.session["user_email"] = user_info.get("email")

            return RedirectResponse(url=redirect_url)
        except Exception as e:
            db.rollback()
            logger.error(f"Database error saving Google integration: {e}")
            return RedirectResponse(url=f"{redirect_url}?error=database_error")

    except Exception as e:
        logger.error(f"Error in OAuth callback: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/disconnect")
async def disconnect_google(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Disconnect Google account
    """
    # Log request headers for debugging
    logger.info(f"Disconnect endpoint called with headers: {dict(request.headers)}")
    logger.info(f"Request method: {request.method}")

    # Detect if this is a browser request vs API call
    is_browser = 'text/html' in request.headers.get('accept', '')
    logger.info(f"Is browser request: {is_browser}")

    # Get user ID from session
    user_id = request.session.get("user_id")
    logger.info(f"User ID from session: {user_id}")

    # Always clean up session - even if user_id is not found
    if "is_connected" in request.session:
        del request.session["is_connected"]
    if "user_email" in request.session:
        del request.session["user_email"]

    # If user_id is not found, use hardcoded ID for now
    if not user_id:
        # Use hardcoded user ID temporarily
        # TODO: Implement proper authentication
        user_id = "52cb4d8f-ca71-484b-9228-112070c4947a"
        request.session["user_id"] = user_id
        logger.info(f"Using hardcoded user ID: {user_id}")

    # Attempt to update the database if we have a user ID
    try:
        # Update database
        query = db.query(GoogleIntegration).filter(
            GoogleIntegration.user_id == user_id,
            GoogleIntegration.status == "active"
        )

        email = request.session.get("user_email")
        if email:
            query = query.filter(GoogleIntegration.email == email)

        integrations = query.all()

        # Even if no integrations found, we still want to clean session and redirect
        if not integrations:
            logger.warning(f"No active integrations found for user {user_id}")

            # Always redirect browser back to home page after disconnecting
            if is_browser:
                return RedirectResponse(
                    url="/",
                    status_code=status.HTTP_302_FOUND
                )

            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"message": "No active Google integrations found"}
            )

        # Update all matching integrations
        for integration in integrations:
            integration.status = "disconnected"

        db.commit()

        # Always redirect browser back to home page after disconnecting
        if is_browser:
            return RedirectResponse(
                url="/",
                status_code=status.HTTP_302_FOUND
            )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": f"Successfully disconnected {len(integrations)} Google integration(s)"}
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Error disconnecting Google account: {e}")

        # Always redirect browser back to home page after error
        if is_browser:
            return RedirectResponse(
                url=f"/?error=disconnect_failed&message={str(e)}",
                status_code=status.HTTP_302_FOUND
            )

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": f"Failed to disconnect: {str(e)}"}
        )

@router.get("/feed/tiles")
async def get_feed_tiles(user_id: str, db=Depends(get_db)):
    """
    Get feed tiles for a user, fetching new data if needed
    """
    try:
        logger.info(f"Starting feed tiles request for user {user_id}")

        # Convert user_id to UUID
        try:
            user_uuid = UUID(user_id)
            logger.info(f"Converted user_id to UUID: {user_uuid}")
        except ValueError as e:
            logger.error(f"Invalid user_id format: {e}")
            raise HTTPException(status_code=400, detail="Invalid user ID format")

        # Get user's Google integration
        integration = db.query(GoogleIntegration).filter(
            GoogleIntegration.user_id == user_uuid,
            GoogleIntegration.status == "active"
        ).first()

        if not integration:
            logger.error(f"No active Google integration found for user {user_uuid}")
            raise HTTPException(status_code=404, detail="No active Google integration found")

        logger.info(f"Found active Google integration for user {user_uuid}")

        # Get existing tiles
        existing_tiles = db.query(Tiles).filter(
            Tiles.user_id == user_uuid
        ).all()

        logger.info(f"Found {len(existing_tiles)} existing tiles for user {user_uuid}")

        # Check if we need to fetch new data
        need_fetch = True
        if existing_tiles:
            latest_tile = max(existing_tiles, key=lambda t: t.created_at)
            time_diff = datetime.now(timezone.utc) - latest_tile.created_at

            if time_diff.total_seconds() < 300:  # 5 minutes
                need_fetch = False
                logger.info("Using existing tiles - last update less than 5 minutes ago")
            else:
                logger.info(f"Fetching new data - last update was {time_diff.total_seconds()} seconds ago")
        else:
            logger.info("No existing tiles found - fetching new data")

        if need_fetch:
            try:
                # Build credentials dictionary
                credentials = {
                    "access_token": integration.access_token,
                    "refresh_token": integration.refresh_token,
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "client_id": os.getenv("GOOGLE_CLIENT_ID"),
                    "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
                    "scopes": integration.scopes.split(",") if isinstance(integration.scopes, str) else integration.scopes
                }

                # Connect to Gmail service
                if not await get_gmail_service(db).connect(credentials):
                    raise HTTPException(status_code=500, detail="Failed to connect to Gmail API")

                logger.info("Successfully connected to Gmail API")

                # Fetch new messages
                messages = await get_gmail_service(db).get_messages(max_results=10)
                logger.info(f"Fetched {len(messages)} new messages from Gmail")

                # Process messages into tiles
                if messages:
                    processed_tiles = []
                    for message in messages:
                        try:
                            # Extract headers
                            headers = message.get("payload", {}).get("headers", [])
                            subject = next((h["value"] for h in headers if h["name"].lower() == "subject"), "No Subject")
                            date = next((h["value"] for h in headers if h["name"].lower() == "date"), None)
                            from_header = next((h["value"] for h in headers if h["name"].lower() == "from"), None)

                            # Create tile
                            tile = {
                                "id": message["id"],
                                "title": subject,
                                "content": message.get("snippet", ""),
                                "created_at": date,
                                "metadata": {
                                    "from": from_header,
                                    "platform_specific_data": {
                                        "message_id": message["id"],
                                        "thread_id": message.get("threadId"),
                                        "label_ids": message.get("labelIds", [])
                                    }
                                }
                            }
                            processed_tiles.append(tile)
                        except Exception as e:
                            logger.error(f"Error processing message {message.get('id', 'unknown')}: {e}")
                            continue

                    return {"tiles": processed_tiles}

                return {"tiles": []}

            except Exception as e:
                logger.error(f"Error fetching Gmail data: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        return {"tiles": existing_tiles}

    except Exception as e:
        logger.error(f"Error in get_feed_tiles: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/feed-tabs")
async def get_feed_tabs(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Get available feed tabs from layout tabs
    """
    try:
        # Get user ID from session
        user_id = request.session.get("user_id")
        if not user_id:
            # Check if we have any active integrations
            integration = db.query(GoogleIntegration).filter(
                GoogleIntegration.status == 'active'
            ).order_by(GoogleIntegration.created_at.desc()).first()

            if integration:
                user_id = str(integration.user_id)
                request.session["user_id"] = user_id
                logger.info(f"Found active integration for user: {user_id}")
            else:
                logger.warning("No active integrations found")
                return {
                    "feed_tabs": [],
                    "has_integrations": False
                }

        # Convert user_id to UUID if it's a string
        try:
            user_uuid = UUID(user_id) if isinstance(user_id, str) else user_id
        except ValueError as e:
            logger.error(f"Invalid UUID format for user_id: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid UUID format: {str(e)}"
            )

        # Get all active Google integrations for this user
        integrations = db.query(GoogleIntegration).filter(
            GoogleIntegration.user_id == user_uuid,
            GoogleIntegration.status == "active"
        ).all()

        # Get layout tabs that correspond to Google feed types
        layout_tabs = db.query(LayoutTabs).filter(
            LayoutTabs.user_id == user_uuid,
            LayoutTabs.name.in_(["gmail", "calendar", "todo", "social"])
        ).order_by(LayoutTabs.order).all()

        # If no tabs exist, create default ones
        if not layout_tabs:
            try:
                # Create default tabs in a transaction
                default_tabs = [
                    {
                        "name": "gmail",
                        "tab_id": "gmail",
                        "icon": "email",
                        "order": 0,
                        "is_default": True
                    },
                    {
                        "name": "calendar",
                        "tab_id": "calendar",
                        "icon": "calendar_today",
                        "order": 1,
                        "is_default": False
                    },
                    {
                        "name": "todo",
                        "tab_id": "todo",
                        "icon": "check_circle",
                        "order": 2,
                        "is_default": False
                    },
                    {
                        "name": "social",
                        "tab_id": "social",
                        "icon": "people",
                        "order": 3,
                        "is_default": False
                    }
                ]

                layout_tabs = []
                for tab_data in default_tabs:
                    try:
                        # Generate UUID for the tab
                        tab_id = uuid4()
                        logger.info(f"Creating tab {tab_data['name']} with UUID: {tab_id}")

                        # Create new tab with UUID using GUID type
                        new_tab = LayoutTabs(
                            id=tab_id,  # GUID type will handle the conversion
                            user_id=user_uuid,  # GUID type will handle the conversion
                            name=tab_data["name"],
                            tab_id=tab_data["tab_id"],
                            icon=tab_data["icon"],
                            order=tab_data["order"],
                            is_default=tab_data["is_default"]
                        )
                        db.add(new_tab)
                        layout_tabs.append(new_tab)

                        # Commit after each tab to ensure proper UUID handling
                        db.commit()
                        logger.info(f"Successfully created tab {tab_data['name']}")

                    except Exception as e:
                        logger.error(f"Error creating tab {tab_data['name']}: {e}")
                        db.rollback()
                        raise

            except Exception as e:
                db.rollback()
                logger.error(f"Failed to create default tabs: {e}")
                # Continue with empty tabs list rather than failing
                layout_tabs = []

        # Format tab info
        feed_tabs = []
        for tab in layout_tabs:
            # Handle scopes whether it's a string or list
            has_scope = False
            for integration in integrations:
                scopes = integration.scopes
                scopes_str = scopes if isinstance(scopes, str) else ",".join(scopes) if isinstance(scopes, list) else ""
                scopes_str = scopes_str.lower()

                if (tab.name.lower() in scopes_str or  # Direct scope match
                    (tab.name.lower() == "gmail" and "gmail.readonly" in scopes_str) or  # Gmail special case
                    (tab.name.lower() == "calendar" and "calendar.readonly" in scopes_str)):  # Calendar special case
                    has_scope = True
                    break

            feed_tabs.append({
                "id": str(tab.id),  # Convert UUID to string for JSON response
                "name": tab.name,
                "tab_id": tab.tab_id,
                "icon": tab.icon,
                "order": tab.order,
                "has_scope": has_scope
            })

        logger.info(f"Returning {len(feed_tabs)} feed tabs for user {user_id}")
        return {
            "feed_tabs": feed_tabs,
            "has_integrations": len(integrations) > 0
        }
    except Exception as e:
        logger.error(f"Error fetching feed tabs: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": f"Failed to fetch feed tabs: {str(e)}"}
        )

@router.get("/status")
async def get_google_status(
    request: Request,
    db: Session = Depends(get_db),
    auth_manager: GoogleAuthManager = Depends(get_auth_manager)
):
    """
    Get detailed Google integration status
    """
    # Get user ID from session
    user_id = request.session.get("user_id")
    if not user_id:
        # Check if we have any active integrations
        integration = db.query(GoogleIntegration).filter(
            GoogleIntegration.status == 'active'
        ).order_by(GoogleIntegration.created_at.desc()).first()

        if integration:
            user_id = str(integration.user_id)
            request.session["user_id"] = user_id
            logger.info(f"Found active integration for user: {user_id}")
        else:
            logger.warning("No active integrations found")
            return {
                "has_integrations": False,
                "integrations": []
            }

    try:
        # Get all Google integrations for this user
        integrations = db.query(GoogleIntegration).filter(
            GoogleIntegration.user_id == user_id
        ).all()

        if not integrations:
            return {
                "has_integrations": False,
                "integrations": []
            }

        # Format integration info
        integration_info = []
        for integration in integrations:
            # Check if credentials are valid
            credentials = {
                "access_token": integration.access_token,
                "refresh_token": integration.refresh_token,
                "token_uri": "https://oauth2.googleapis.com/token",
                "client_id": os.getenv("GOOGLE_CLIENT_ID", ""),
                "client_secret": os.getenv("GOOGLE_CLIENT_SECRET", ""),
                "scopes": integration.scopes.split(",") if isinstance(integration.scopes, str) else integration.scopes
            }

            token_valid = integration.status == "active" and auth_manager.validate_and_refresh(credentials)

            # If token was refreshed, update in database
            if token_valid and credentials.get("access_token") != integration.access_token:
                integration.access_token = credentials.get("access_token")
                if "expiry" in credentials:
                    integration.token_expiry = datetime.fromtimestamp(credentials["expiry"])
                db.commit()

            # Build scopes into feature access
            scopes_str = integration.scopes if isinstance(integration.scopes, str) else ",".join(integration.scopes) if isinstance(integration.scopes, list) else ""
            scopes_str = scopes_str.lower()

            has_gmail = "gmail.readonly" in scopes_str
            has_calendar = "calendar.readonly" in scopes_str

            integration_info.append({
                "id": integration.id,
                "email": integration.email,
                "status": integration.status,
                "is_valid": token_valid,
                "created_at": integration.created_at.isoformat() if integration.created_at else None,
                "updated_at": integration.updated_at.isoformat() if integration.updated_at else None,
                "features": {
                    "gmail": has_gmail,
                    "calendar": has_calendar,
                    "todo": False,  # Not implemented yet
                    "social": False  # Not implemented yet
                }
            })

        return {
            "has_integrations": True,
            "integrations": integration_info
        }
    except Exception as e:
        logger.error(f"Error getting Google status: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": f"Failed to get Google status: {str(e)}"}
        )
