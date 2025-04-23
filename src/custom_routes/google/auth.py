"""
Consolidated Google authentication routes.
Handles Google OAuth flow and credential management.
"""

import logging
import uuid
import requests
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, Request, HTTPException, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.utils.database import get_db
from src.models.google_integration import GoogleIntegration
from src.models.users import Users
from src.providers.google import GoogleAuthManager
from src.utils.google_credentials import (
    store_credentials_in_database_url,
    clear_credentials_from_database_url
)
from src.utils.logger import get_logger

# Configure logging
logger = get_logger(__name__)

# Create router
router = APIRouter(prefix="/api/google", tags=["google"])

# OAuth scopes
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile'
]

# Google API endpoints
GOOGLE_TOKEN_URI = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URI = "https://www.googleapis.com/oauth2/v3/userinfo"

# Pydantic models
class UserResponse(BaseModel):
    id: str
    email: str = ""

class AuthUrlResponse(BaseModel):
    auth_url: str

class GoogleCredentialsResponse(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_uri: str
    client_id: str
    client_secret: str
    scopes: List[str]
    expiry: Optional[str] = None

async def store_credentials(
    db: Session,
    user_id: str,
    email: str,
    credentials_dict: Dict[str, Any],
    scopes: List[str]
) -> None:
    """Store Google credentials in the database"""
    try:
        # Check for existing integration
        integration = db.query(GoogleIntegration).filter(
            GoogleIntegration.user_id == user_id
        ).first()

        if integration:
            # Update existing integration
            integration.email = email
            integration.credentials = credentials_dict
            integration.scopes = scopes
            integration.updated_at = datetime.now(timezone.utc)
        else:
            # Create new integration
            integration = GoogleIntegration(
                user_id=user_id,
                email=email,
                credentials=credentials_dict,
                scopes=scopes,
                status='active'
            )
            db.add(integration)

        db.commit()
        logger.info(f"Stored credentials for user {user_id}")
    except Exception as e:
        logger.error(f"Error storing credentials: {e}")
        db.rollback()
        raise

# Helper functions
def get_auth_manager(db: Session = Depends(get_db)):
    """Get GoogleAuthManager instance"""
    return GoogleAuthManager(db)

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

    # If user_id is not found, use hardcoded ID for now
    # TODO: Implement proper authentication
    user_id = "52cb4d8f-ca71-484b-9228-112070c4947a"
    request.session["user_id"] = user_id
    logger.info(f"Using hardcoded user ID: {user_id}")

    return UserResponse(
        id=user_id,
        email=""
    )

# Routes
@router.get("/auth")
async def google_auth(
    request: Request,
    auth_manager: GoogleAuthManager = Depends(get_auth_manager)
):
    """Start Google OAuth flow"""
    try:
        # Generate state token
        state = str(uuid.uuid4())
        request.session["oauth_state"] = state

        # Get the authorization URL with correct redirect URI
        base_url = str(request.base_url)
        # Replace port if needed
        if ":8765" in base_url:
            base_url = base_url.replace(":8765", ":8000")
        
        # Replace IP with localhost for Google OAuth
        base_url = base_url.replace("0.0.0.0", "localhost").replace("127.0.0.1", "localhost")
        
        redirect_uri = f"{base_url.rstrip('/')}/api/google/callback"
        
        logger.info(f"Using redirect URI: {redirect_uri}")
        
        auth_url = auth_manager.get_authorization_url(
            redirect_uri=redirect_uri,
            state=state
        )

        return {"auth_url": auth_url}
    except Exception as e:
        logger.error(f"Error starting OAuth flow: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/callback")
async def google_callback(
    request: Request,
    code: str,
    state: Optional[str] = None,
    db: Session = Depends(get_db),
    auth_manager: GoogleAuthManager = Depends(get_auth_manager)
):
    """Handle Google OAuth callback"""
    try:
        # Verify state
        session_state = request.session.get("oauth_state")
        if not session_state or session_state != state:
            logger.warning(f"State mismatch: {session_state} != {state}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid state parameter"
            )

        # Get the callback URL with correct port
        base_url = str(request.base_url)
        if ":8765" in base_url:
            base_url = base_url.replace(":8765", ":8000")
        
        # Replace IP with localhost for Google OAuth
        base_url = base_url.replace("0.0.0.0", "localhost").replace("127.0.0.1", "localhost")
        
        redirect_uri = f"{base_url.rstrip('/')}/api/google/callback"
        
        logger.info(f"Using callback URI: {redirect_uri}")

        # Exchange code for tokens
        credentials_dict = auth_manager.exchange_code(code, redirect_uri)

        if not credentials_dict:
            logger.error("Failed to exchange code for tokens")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to exchange code for tokens"
            )

        # Get user info
        user_info = await get_user_info(credentials_dict["access_token"])
        if not user_info:
            logger.error("Failed to get user info")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get user info"
            )

        # Get or create user
        user = db.query(Users).filter(Users.email == user_info["email"]).first()
        if not user:
            user = Users(
                email=user_info["email"],
                name=user_info.get("name", ""),
                is_active=True
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        # Store credentials
        integration = db.query(GoogleIntegration).filter(
            GoogleIntegration.user_id == str(user.id)
        ).first()

        if integration:
            integration.access_token = credentials_dict["access_token"]
            integration.refresh_token = credentials_dict.get("refresh_token")
            integration.token_expiry = datetime.utcnow() + timedelta(seconds=credentials_dict.get("expires_in", 3600))
            integration.email = user_info["email"]
        else:
            integration = GoogleIntegration(
                user_id=str(user.id),
                email=user_info["email"],
                access_token=credentials_dict["access_token"],
                refresh_token=credentials_dict.get("refresh_token"),
                token_expiry=datetime.utcnow() + timedelta(seconds=credentials_dict.get("expires_in", 3600))
            )
            db.add(integration)

        db.commit()

        # Store user info in session
        request.session["user_id"] = str(user.id)
        request.session["user_email"] = user_info["email"]
        request.session["is_connected"] = True

        # Redirect to home page
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error in callback: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/store-in-db-url")
async def store_in_db_url(request: Request):
    """Set flag to store credentials in DATABASE_URL"""
    # Generate state token
    state = str(uuid.uuid4())
    request.session["oauth_state"] = state
    request.session["store_in_db_url"] = True
    
    # Log the state being set
    logger.info(f"Setting oauth_state in session: {state}")
    
    return RedirectResponse(url="/api/google/auth", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/status")
async def google_status(
    request: Request,
    user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get Google connection status"""
    try:
        # Check for active Google integration
        integration = db.query(GoogleIntegration).filter(
            GoogleIntegration.user_id == user.id,
            GoogleIntegration.status == "active"
        ).first()

        if not integration:
            return {
                "is_connected": False,
                "email": None
            }

        return {
            "is_connected": True,
            "email": integration.email,
            "scopes": integration.scopes.split(",") if isinstance(integration.scopes, str) else integration.scopes
        }
    except Exception as e:
        logger.error(f"Error getting Google status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/disconnect")
async def google_disconnect(
    request: Request,
    user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Disconnect Google account"""
    try:
        # Find active integration
        integration = db.query(GoogleIntegration).filter(
            GoogleIntegration.user_id == user.id,
            GoogleIntegration.status == "active"
        ).first()

        if integration:
            # Update status
            integration.status = "disconnected"
            integration.updated_at = datetime.now(timezone.utc)
            db.commit()

        # Clear session
        if "is_connected" in request.session:
            del request.session["is_connected"]
        if "user_email" in request.session:
            del request.session["user_email"]

        # Also clear DATABASE_URL if it contains credentials
        clear_credentials_from_database_url()

        return {"success": True, "message": "Google account disconnected"}
    except Exception as e:
        logger.error(f"Error disconnecting Google account: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# Helper functions
async def get_user_info(access_token: str) -> Optional[Dict[str, Any]]:
    """Get user info from Google API"""
    try:
        response = requests.get(
            GOOGLE_USERINFO_URI,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Error getting user info: {response.status_code} {response.text}")
            return None
    except Exception as e:
        logger.error(f"Error getting user info: {str(e)}")
        return None


