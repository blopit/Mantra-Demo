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

import aiohttp
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse, JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from sqlalchemy import select

from src.utils.database import get_db
from src.models.users import Users
from src.models.google_auth import GoogleAuth
from src.models.google_integration import GoogleIntegration

# Configure logging
logger = logging.getLogger(__name__)

async def get_current_user(request: Request, db: Session = Depends(get_db)) -> Users:
    """
    Get the current authenticated user from the session.
    
    Args:
        request: FastAPI request object
        db: Database session
        
    Returns:
        Users: Current authenticated user
        
    Raises:
        HTTPException: If user is not authenticated
    """
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
        
    user = db.query(Users).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
        
    return user

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
    request: Request,
    scopes: Optional[List[str]] = None,
    access_type: str = "offline",
    include_granted_scopes: bool = False
):
    """
    Get Google OAuth URL for authentication.
    
    Args:
        request: FastAPI request object
        scopes: Optional list of scopes to request
        access_type: Whether to request offline access (for refresh tokens)
        include_granted_scopes: Whether to include previously granted scopes (defaults to False)
        
    Returns:
        AuthUrlResponse: Object containing the authorization URL
    """
    try:
        flow = build_google_oauth(scopes)
        
        # Generate authorization URL with specified parameters
        authorization_url, state = flow.authorization_url(
            access_type=access_type,
            include_granted_scopes="false",  # Never include previously granted scopes
            prompt="consent"  # Always show consent screen to ensure correct scopes
        )
        
        # Store state in session with the correct key
        request.session["oauth_state"] = state
        
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
    code: str,
    state: str,
    db: Session = Depends(get_db)
):
    """Handle Google OAuth callback."""
    try:
        # Verify state to prevent CSRF
        stored_state = request.session.get("oauth_state")
        if not stored_state or stored_state != state:
            raise HTTPException(status_code=400, detail="Invalid state parameter")
        
        # Get token from Google
        token = await get_google_token(code)
        if not token:
            raise HTTPException(status_code=400, detail="Failed to get token")
        
        # Get user info from Google
        user_info = await get_google_user_info(token["access_token"])
        if not user_info:
            raise HTTPException(status_code=400, detail="Failed to get user info")
            
        # Find or create user
        user = db.query(Users).filter_by(email=user_info["email"]).first()
        if not user:
            user = Users(
                id=str(uuid.uuid4()),
                email=user_info["email"],
                name=user_info.get("name", ""),
                profile_picture=user_info.get("picture", "")
            )
            db.add(user)
            db.commit()
            
        # Store user in session
        request.session["user"] = {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "profile_picture": user.profile_picture
        }
        
        # Check if integration already exists
        integration = db.query(GoogleIntegration).filter(
            GoogleIntegration.user_id == user.id,
            GoogleIntegration.google_account_id == user_info["sub"]
        ).first()
        
        if not integration:
            # Create new integration
            integration = GoogleIntegration(
                id=str(uuid.uuid4()),
                user_id=user.id,
                google_account_id=user_info["sub"],
                email=user_info["email"],
                service_name="google",
                is_active=True,
                status="connected",
                access_token=token["access_token"],
                refresh_token=token.get("refresh_token"),
                expires_at=datetime.utcnow() + timedelta(seconds=token["expires_in"]),
                scopes=",".join(token["scope"] if isinstance(token["scope"], list) else token["scope"].split(" ")),
                settings=json.dumps({"profile": user_info})
            )
            db.add(integration)
        else:
            # Update existing integration
            integration.access_token = token["access_token"]
            if "refresh_token" in token:
                integration.refresh_token = token["refresh_token"]
            integration.expires_at = datetime.utcnow() + timedelta(seconds=token["expires_in"])
            integration.scopes = ",".join(token["scope"] if isinstance(token["scope"], list) else token["scope"].split(" "))
            integration.is_active = True
            integration.status = "connected"
            integration.settings = json.dumps({"profile": user_info})
            integration.disconnected_at = None
        
        db.commit()
        
        # Redirect to frontend with success
        return RedirectResponse(url="/accounts")
        
    except Exception as e:
        logger.error(f"Error in Google callback: {str(e)}")
        # Redirect to frontend with error
        return RedirectResponse(url=f"/signin?error={str(e)}")

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
        integration = db.query(GoogleIntegration).filter_by(is_active=True).first()
        if integration:
            user = db.query(Users).filter_by(id=integration.user_id).first()
            if user:
                return {
                    "connected": True,
                    "email": integration.email,
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
        # Get auth record from database
        result = await db.execute(select(GoogleAuth))
        auth = result.scalar_one_or_none()
        if not auth:
            # Try to get from GoogleIntegration table
            result = await db.execute(select(GoogleIntegration).where(GoogleIntegration.is_active == True))
            integration = result.scalar_one_or_none()
            if not integration:
                raise HTTPException(status_code=404, detail="No Google account connected")
            
            # Revoke token with Google if available
            if integration.access_token:
                try:
                    # Attempt to revoke the token
                    response = google_requests.Request().session.post(
                        "https://oauth2.googleapis.com/revoke",
                        params={"token": integration.access_token},
                        headers={"Content-Type": "application/x-www-form-urlencoded"}
                    )
                    
                    if not response.ok:
                        logger.warning(f"Failed to revoke token: {response.text}")
                except Exception as e:
                    logger.warning(f"Error revoking token: {str(e)}")
            
            # Mark integration as inactive
            integration.is_active = False
            integration.status = "disconnected"
            integration.disconnected_at = datetime.utcnow()
            await db.commit()
            
            return JSONResponse({
                "success": True,
                "message": "Successfully disconnected from Google"
            })
            
        # Revoke token with Google if available
        if auth.access_token:
            try:
                # Attempt to revoke the token
                response = google_requests.Request().session.post(
                    "https://oauth2.googleapis.com/revoke",
                    params={"token": auth.access_token},
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                
                if not response.ok:
                    logger.warning(f"Failed to revoke token: {response.text}")
            except Exception as e:
                logger.warning(f"Error revoking token: {str(e)}")
        
        # Delete the auth record
        await db.delete(auth)
        await db.commit()
        
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

async def get_google_token(code: str) -> Optional[Dict[str, Any]]:
    """
    Exchange authorization code for tokens from Google.
    
    Args:
        code: Authorization code from Google OAuth flow
        
    Returns:
        Dict containing token information or None if request fails
    """
    try:
        flow = build_google_oauth()
        # fetch_token is synchronous, don't use await
        token = flow.fetch_token(code=code)
        return token
    except Exception as e:
        logger.error(f"Error getting Google token: {str(e)}")
        return None

async def get_google_user_info(access_token: str) -> Optional[Dict[str, Any]]:
    """
    Get user info from Google using access token.
    
    Args:
        access_token: Valid Google OAuth access token
        
    Returns:
        Dict containing user information or None if request fails
    """
    try:
        headers = {"Authorization": f"Bearer {access_token}"}
        async with aiohttp.ClientSession() as session:
            async with session.get(GOOGLE_USERINFO_URI, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"Error getting user info: {await response.text()}")
                    return None
    except Exception as e:
        logger.error(f"Error getting user info: {str(e)}")
        return None
