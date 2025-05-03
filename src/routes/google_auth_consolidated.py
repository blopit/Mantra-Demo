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
        
    result = await db.execute(select(Users).filter_by(id=user_id))
    user = result.scalars().first()
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
    
    # Get credentials from environment
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    
    # Validate credentials
    if not client_id or not client_secret:
        logger.error(f"Missing Google OAuth credentials: client_id={bool(client_id)}, client_secret={bool(client_secret)}")
        raise ValueError("Missing required Google OAuth credentials. Check GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET environment variables.")
        
    client_config = {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": GOOGLE_OAUTH_TOKEN_URI,
            "redirect_uris": [REDIRECT_URI],
        }
    }
    
    try:
        flow = Flow.from_client_config(
            client_config,
            scopes=scopes,
            redirect_uri=REDIRECT_URI
        )
        return flow
    except Exception as e:
        logger.error(f"Error creating Google OAuth flow: {str(e)}")
        raise ValueError(f"Failed to create Google OAuth flow: {str(e)}")

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
        logger.info(f"Generated auth URL with state: {state}")
        
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
        logger.info(f"Verifying state: received={state}, stored={stored_state}")
        
        if not stored_state:
            logger.error("No OAuth state found in session")
            return RedirectResponse(url="/signin?error=No OAuth state found in session", status_code=307)
            
        if stored_state != state:
            logger.error(f"Invalid state parameter: received={state}, expected={stored_state}")
            return RedirectResponse(url="/signin?error=Invalid state parameter", status_code=307)
        
        # Get token from Google
        logger.info(f"Getting token from Google with code: {code[:10]}...")
        token = await get_google_token(code)
        if not token:
            logger.error("Failed to get token from Google API")
            return RedirectResponse(url="/signin?error=Failed to get token from Google API", status_code=307)
        
        # Get user info from Google
        logger.info("Getting user info from Google API")
        user_info = await get_google_user_info(token["access_token"])
        if not user_info:
            logger.error("Failed to get user info from Google API")
            return RedirectResponse(url="/signin?error=Failed to get user info from Google API", status_code=307)
        
        logger.info(f"Got user info: email={user_info.get('email')}")
            
        # Find or create user
        user_result = await db.execute(select(Users).filter_by(email=user_info["email"]))
        user = user_result.scalars().first()
        if not user:
            logger.info(f"Creating new user with email: {user_info.get('email')}")
            user = Users(
                id=user_info["sub"],  # Use Google's sub as the user ID
                email=user_info["email"],
                name=user_info.get("name", ""),
                profile_picture=user_info.get("picture", "")
            )
            db.add(user)
            await db.commit()
            logger.info(f"Created new user with ID: {user.id}")
        else:
            logger.info(f"Found existing user with ID: {user.id}")
            
        # Store user in session
        request.session["user"] = {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "profile_picture": user.profile_picture
        }
        logger.info("Stored user in session")
        
        # Check if integration already exists
        integration_result = await db.execute(select(GoogleIntegration).filter(
            GoogleIntegration.user_id == user.id,
            GoogleIntegration.google_account_id == user_info["sub"]
        ))
        integration = integration_result.scalars().first()

        if not integration:
            # Create new integration
            logger.info("Creating new Google integration")
            integration = GoogleIntegration(
                id=user_info["sub"],  # Use Google's sub as the integration ID
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
            logger.info(f"Created new integration with ID: {integration.id}")
        else:
            # Update existing integration
            logger.info(f"Updating existing integration with ID: {integration.id}")
            integration.access_token = token["access_token"]
            if "refresh_token" in token:
                integration.refresh_token = token["refresh_token"]
            integration.expires_at = datetime.utcnow() + timedelta(seconds=token["expires_in"])
            integration.scopes = ",".join(token["scope"] if isinstance(token["scope"], list) else token["scope"].split(" "))
            integration.is_active = True
            integration.status = "connected"
            integration.settings = json.dumps({"profile": user_info})
            integration.disconnected_at = None
        
        await db.commit()
        logger.info("Saved integration to database")
        
        # Redirect to frontend with success
        logger.info("Authentication successful, redirecting to /accounts")
        return RedirectResponse(url="/accounts", status_code=307)
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"Error in Google callback: {str(e)}\n{error_details}")
        # Redirect to frontend with error
        error_msg = str(e).replace("'", "").replace('"', "")
        return RedirectResponse(url=f"/signin?error={error_msg}", status_code=307)

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
        if user and user.get("id"):  # Make sure we have an ID
            return {
                "connected": True,
                "email": user["email"],
                "user": {
                    "id": user["id"],
                    "email": user["email"],
                    "name": user.get("name", ""),
                    "profile_picture": user.get("profile_picture", "")
                }
            }
            
        # If not in session, check database
        # This is useful for API clients that don't use sessions
        user_id = request.session.get("user", {}).get("id")
        if not user_id:
            return {"connected": False}

        integration_result = await db.execute(select(GoogleIntegration).filter_by(user_id=user_id, is_active=True))
        integration = integration_result.scalars().first()

        if integration:
            user_result = await db.execute(select(Users).filter_by(id=user_id))
            user = user_result.scalars().first()
            if user:
                return {
                    "connected": True,
                    "email": integration.email,
                    "user": {
                        "id": user.id,
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
    """Disconnect Google integration."""
    user_id = request.session.get("user", {}).get("id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    integration_result = await db.execute(select(GoogleIntegration).filter_by(user_id=user_id, is_active=True))
    integration = integration_result.scalars().first()

    if not integration:
        # Also check the older GoogleAuth model for potential migration cases
        auth_result = await db.execute(select(GoogleAuth).filter_by(user_id=user_id))
        auth = auth_result.scalars().first()
        if not auth:
             raise HTTPException(status_code=404, detail="Google integration or auth record not found")
        else:
            # Found an old auth record, revoke and delete it
            if auth.access_token:
                # (Revoke token logic - kept concise for example)
                pass 
            await db.delete(auth)
            await db.commit()
            # Clear session info if needed
            # request.session.pop("user", None)
            # request.session.pop("tokens", None)
            return JSONResponse({"success": True, "message": "Successfully disconnected legacy Google auth"})

    # Found active integration, proceed to disconnect it
    if integration.access_token:
        try:
            # Attempt to revoke the token
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://oauth2.googleapis.com/revoke",
                    params={"token": integration.access_token},
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                ) as response:
                    if not response.ok:
                        logger.warning(f"Failed to revoke token: {await response.text()}")
        except Exception as e:
            logger.warning(f"Error revoking token: {str(e)}")

    # Mark integration as inactive or delete it
    integration.is_active = False
    integration.status = "disconnected"
    integration.disconnected_at = datetime.utcnow()
    # Or alternatively: await db.delete(integration)
    await db.commit()

    # Clear relevant session data if needed
    # request.session.pop("user", None)
    # request.session.pop("tokens", None)

    return JSONResponse({
        "success": True,
        "message": "Successfully disconnected from Google"
    })

@router.get("/refresh")
async def refresh_token(request: Request, db: Session = Depends(get_db)):
    """Refresh Google access token."""
    user_id = request.session.get("user", {}).get("id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    integration_result = await db.execute(select(GoogleIntegration).filter_by(user_id=user_id, is_active=True))
    integration = integration_result.scalars().first()

    if not integration:
        raise HTTPException(status_code=404, detail="Active Google integration not found")

    refresh_token = integration.refresh_token
    if not refresh_token:
        # If integration lacks refresh token, try the old GoogleAuth model
        auth_result = await db.execute(select(GoogleAuth).filter_by(user_id=user_id))
        auth = auth_result.scalars().first()
        if auth and auth.refresh_token:
            refresh_token = auth.refresh_token
        else:
            raise HTTPException(status_code=400, detail="No refresh token available for this integration")

    # Request new access token using aiohttp
    token_request_data = {
        "client_id": os.getenv("GOOGLE_CLIENT_ID"),
        "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }

    async with aiohttp.ClientSession() as http_session:
        async with http_session.post(GOOGLE_OAUTH_TOKEN_URI, data=token_request_data) as response:
            if not response.ok:
                error_text = await response.text()
                logger.error(f"Failed to refresh token: {response.status} - {error_text}")
                raise HTTPException(status_code=400, detail=f"Failed to refresh token: {error_text}")
            token_data = await response.json()

    # Update the integration record in the database
    integration.access_token = token_data["access_token"]
    integration.expires_at = datetime.utcnow() + timedelta(
        seconds=token_data.get("expires_in", 3600)
    )
    # Optionally update scopes if they changed
    if 'scope' in token_data:
         integration.scopes = ",".join(token_data["scope"] if isinstance(token_data["scope"], list) else token_data["scope"].split(" "))
         
    await db.commit()

    # Optionally update session tokens if needed
    # request.session["tokens"] = {...} 

    return {"success": True, "message": "Token refreshed successfully"}

async def get_google_token(code: str) -> Optional[Dict[str, Any]]:
    """
    Exchange authorization code for tokens from Google.
    
    Args:
        code: Authorization code from Google OAuth flow
        
    Returns:
        Dict containing token information or None if request fails
    """
    try:
        # Build the OAuth flow
        flow = build_google_oauth()
        
        # Prepare token request data for manual API call
        token_data = {
            "code": code,
            "client_id": os.getenv("GOOGLE_CLIENT_ID"),
            "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
            "redirect_uri": REDIRECT_URI,
            "grant_type": "authorization_code"
        }
        
        # Make token request using aiohttp (asynchronous)
        async with aiohttp.ClientSession() as session:
            logger.info(f"Requesting token from {GOOGLE_OAUTH_TOKEN_URI}")
            async with session.post(
                GOOGLE_OAUTH_TOKEN_URI, 
                data=token_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Token exchange failed: {response.status} - {error_text}")
                    return None
                
                token_info = await response.json()
                logger.info("Successfully obtained token from Google")
                return token_info
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
