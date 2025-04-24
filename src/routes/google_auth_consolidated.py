"""
Consolidated Google authentication module for Mantra Demo.

This module provides a unified interface for Google OAuth authentication,
combining functionality from multiple existing modules.
"""

import os
import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse, JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from src.utils.database import get_db
from src.models.users import Users
from src.models.google_auth import GoogleAuth
from src.models.google_integration import GoogleIntegration

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/google", tags=["Google Authentication"])

# Constants
GOOGLE_OAUTH_TOKEN_URI = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URI = "https://www.googleapis.com/oauth2/v3/userinfo"

# Default scopes for Google OAuth
DEFAULT_SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/userinfo.email"
]

# Get the redirect URI from environment or use default
REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/api/google/callback")

# Pydantic models for responses
class AuthUrlResponse(BaseModel):
    auth_url: str

class GoogleStatusResponse(BaseModel):
    connected: bool
    email: Optional[str] = None
    user: Optional[Dict[str, Any]] = None

class GoogleCredentialsResponse(BaseModel):
    success: bool
    message: str
    credentials: Optional[Dict[str, Any]] = None

def build_google_oauth(scopes: List[str] = None):
    """Build Google OAuth flow with specified scopes."""
    if scopes is None:
        scopes = DEFAULT_SCOPES
        
    client_config = {
        "web": {
            "client_id": os.getenv("GOOGLE_CLIENT_ID"),
            "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": GOOGLE_OAUTH_TOKEN_URI,
            "redirect_uris": [REDIRECT_URI],
        }
    }
    
    flow = Flow.from_client_config(
        client_config,
        scopes=scopes,
        redirect_uri=REDIRECT_URI
    )
    
    return flow

@router.get("/auth", response_model=AuthUrlResponse)
async def get_auth_url(
    scopes: Optional[List[str]] = None,
    access_type: str = "offline",
    include_granted_scopes: bool = True
):
    """
    Get Google OAuth URL for authentication.
    
    Args:
        scopes: List of OAuth scopes to request
        access_type: Whether to request offline access (for refresh tokens)
        include_granted_scopes: Whether to include previously granted scopes
        
    Returns:
        AuthUrlResponse: Object containing the authorization URL
    """
    try:
        flow = build_google_oauth(scopes)
        
        # Generate authorization URL with specified parameters
        authorization_url, state = flow.authorization_url(
            access_type=access_type,
            include_granted_scopes="true" if include_granted_scopes else "false"
        )
        
        return {"auth_url": authorization_url}
        
    except Exception as e:
        logger.error(f"Error generating auth URL: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error generating auth URL: {str(e)}"
        )

@router.get("/callback")
async def google_callback(
    request: Request, 
    code: Optional[str] = None,
    state: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Handle Google OAuth callback.
    
    This endpoint processes the authorization code returned by Google,
    exchanges it for access and refresh tokens, and stores the user's
    information in the database.
    
    Args:
        request: FastAPI request object
        code: Authorization code from Google
        state: State parameter from authorization request
        db: Database session
        
    Returns:
        RedirectResponse or JSONResponse depending on the Accept header
    """
    try:
        if not code:
            return RedirectResponse(url="/signin?error=No authorization code provided", status_code=302)

        # Exchange the authorization code for tokens
        flow = build_google_oauth()
        flow.fetch_token(code=code)
        credentials = flow.credentials
        
        # Get user info
        service = build("oauth2", "v2", credentials=credentials)
        user_info = service.userinfo().get().execute()
        
        # Create or update user
        user = db.query(Users).filter_by(email=user_info["email"]).first()
        if not user:
            user = Users(
                id=user_info["sub"],  # Use Google's sub field as user ID
                email=user_info["email"],
                name=user_info.get("name"),
                profile_picture=user_info.get("picture")
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            
        # Store credentials
        auth = db.query(GoogleAuth).filter_by(user_id=user.id).first()
        if auth:
            auth.access_token = credentials.token
            auth.refresh_token = credentials.refresh_token
            auth.token_uri = credentials.token_uri
            auth.client_id = credentials.client_id
            auth.client_secret = credentials.client_secret
            auth.scopes = json.dumps(credentials.scopes)
        else:
            auth = GoogleAuth(
                user_id=user.id,
                access_token=credentials.token,
                refresh_token=credentials.refresh_token,
                token_uri=credentials.token_uri,
                client_id=credentials.client_id,
                client_secret=credentials.client_secret,
                scopes=json.dumps(credentials.scopes)
            )
            db.add(auth)
            
        # Also update GoogleIntegration for backward compatibility
        google_integration = db.query(GoogleIntegration).filter_by(
            google_account_id=user_info["sub"]
        ).first()
        
        expires_at = datetime.utcnow() + timedelta(seconds=3600)  # Default 1 hour
        
        if not google_integration:
            google_integration = GoogleIntegration(
                id=str(uuid.uuid4()),
                user_id=user.id,
                google_account_id=user_info["sub"],
                email=user_info["email"],
                access_token=credentials.token,
                refresh_token=credentials.refresh_token,
                expires_at=expires_at,
                scopes=credentials.scopes,
                status="active"
            )
            db.add(google_integration)
        else:
            google_integration.access_token = credentials.token
            if credentials.refresh_token:
                google_integration.refresh_token = credentials.refresh_token
            google_integration.expires_at = expires_at
            google_integration.status = "active"
            
        db.commit()
        
        # Store in session
        request.session["user"] = {
            "id": user_info["sub"],
            "email": user_info["email"],
            "name": user_info.get("name"),
            "picture": user_info.get("picture")
        }
        request.session["tokens"] = {
            "access_token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "id_token": credentials._id_token
        }
        
        # Check if client accepts JSON
        accept_header = request.headers.get("accept", "")
        if "application/json" in accept_header:
            return JSONResponse({
                "success": True,
                "user": {
                    "id": user_info["sub"],
                    "email": user_info["email"],
                    "name": user_info.get("name"),
                    "picture": user_info.get("picture")
                },
                "tokens": {
                    "access_token": credentials.token,
                    "id_token": credentials._id_token
                }
            })
        
        # Default to redirect response
        return RedirectResponse(url="/accounts", status_code=302)
        
    except Exception as e:
        logger.error(f"Error in Google callback: {str(e)}")
        return RedirectResponse(
            url=f"/signin?error={str(e)}",
            status_code=302
        )

@router.get("/status", response_model=GoogleStatusResponse)
async def get_google_status(request: Request, db: Session = Depends(get_db)):
    """
    Get Google integration status.
    
    This endpoint checks if the user is authenticated with Google
    and returns their connection status and user information.
    
    Args:
        request: FastAPI request object
        db: Database session
        
    Returns:
        GoogleStatusResponse: Object containing connection status and user info
    """
    try:
        # First check session (faster)
        user = request.session.get("user")
        if user:
            return {
                "connected": True,
                "email": user["email"],
                "user": user
            }
            
        # If not in session, check database
        # This is useful for API clients that don't use sessions
        auth = db.query(GoogleAuth).first()
        if auth:
            user = db.query(Users).filter_by(id=auth.user_id).first()
            if user:
                return {
                    "connected": True,
                    "email": user.email,
                    "user": {
                        "email": user.email,
                        "name": user.name,
                        "profile_picture": user.profile_picture
                    }
                }
                
        return {"connected": False}
    except Exception as e:
        logger.error(f"Error getting Google status: {str(e)}")
        return {"connected": False}

@router.post("/disconnect")
async def disconnect_google(request: Request, db: Session = Depends(get_db)):
    """
    Disconnect Google account.
    
    This endpoint revokes the Google OAuth tokens and marks
    the integration as inactive in the database.
    
    Args:
        request: FastAPI request object
        db: Database session
        
    Returns:
        JSONResponse: Success message or error
    """
    try:
        # Get user from session
        user = request.session.get("user")
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
            
        # Revoke token with Google
        tokens = request.session.get("tokens", {})
        access_token = tokens.get("access_token")
        
        if access_token:
            try:
                # Attempt to revoke the token
                requests = google_requests.Request()
                response = requests.session.post(
                    "https://oauth2.googleapis.com/revoke",
                    params={"token": access_token},
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                
                if not response.ok:
                    logger.warning(f"Failed to revoke token: {response.text}")
            except Exception as e:
                logger.warning(f"Error revoking token: {str(e)}")
        
        # Remove from database
        auth = db.query(GoogleAuth).filter_by(user_id=user["id"]).first()
        if auth:
            db.delete(auth)
            
        # Also update GoogleIntegration for backward compatibility
        google_integration = db.query(GoogleIntegration).filter_by(
            google_account_id=user["id"]
        ).first()
        
        if google_integration:
            google_integration.status = "inactive"
            google_integration.disconnected_at = datetime.utcnow()
            
        db.commit()
        
        # Clear session
        request.session.pop("user", None)
        request.session.pop("tokens", None)
        
        return JSONResponse({
            "success": True,
            "message": "Successfully disconnected from Google"
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error disconnecting from Google: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error disconnecting: {str(e)}")

@router.get("/refresh")
async def refresh_token(request: Request, db: Session = Depends(get_db)):
    """
    Refresh Google OAuth token.
    
    This endpoint uses the refresh token to obtain a new access token
    when the current one expires.
    
    Args:
        request: FastAPI request object
        db: Database session
        
    Returns:
        GoogleCredentialsResponse: Success status and new credentials
    """
    try:
        # Get user from session
        user = request.session.get("user")
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
            
        # Get tokens from session
        tokens = request.session.get("tokens", {})
        refresh_token = tokens.get("refresh_token")
        
        if not refresh_token:
            # Try to get from database
            auth = db.query(GoogleAuth).filter_by(user_id=user["id"]).first()
            if auth and auth.refresh_token:
                refresh_token = auth.refresh_token
            else:
                raise HTTPException(status_code=400, detail="No refresh token available")
                
        # Request new access token
        token_request_data = {
            "client_id": os.getenv("GOOGLE_CLIENT_ID"),
            "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
            "refresh_token": refresh_token,
            "grant_type": "refresh_token"
        }
        
        response = google_requests.Request().session.post(
            GOOGLE_OAUTH_TOKEN_URI,
            data=token_request_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        if not response.ok:
            raise HTTPException(
                status_code=400, 
                detail=f"Token refresh failed: {response.text}"
            )
            
        token_data = response.json()
        
        # Update session
        tokens["access_token"] = token_data["access_token"]
        request.session["tokens"] = tokens
        
        # Update database
        auth = db.query(GoogleAuth).filter_by(user_id=user["id"]).first()
        if auth:
            auth.access_token = token_data["access_token"]
            
        # Also update GoogleIntegration for backward compatibility
        google_integration = db.query(GoogleIntegration).filter_by(
            google_account_id=user["id"]
        ).first()
        
        if google_integration:
            google_integration.access_token = token_data["access_token"]
            google_integration.expires_at = datetime.utcnow() + timedelta(
                seconds=token_data.get("expires_in", 3600)
            )
            
        db.commit()
        
        return {
            "success": True,
            "message": "Token refreshed successfully",
            "credentials": {
                "access_token": token_data["access_token"],
                "expires_in": token_data.get("expires_in", 3600)
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error refreshing token: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error refreshing token: {str(e)}")
