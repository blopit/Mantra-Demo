"""
FastAPI router for Google authentication endpoints
"""

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, JSONResponse
import os
import logging
from pydantic import BaseModel
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from typing import Optional
import uuid
import requests
import google_auth_oauthlib
from fastapi import HTTPException

# Pydantic models for responses
class AuthUrlResponse(BaseModel):
    auth_url: str

class GoogleStatusResponse(BaseModel):
    connected: bool
    email: Optional[str] = None
    user: Optional[dict] = None

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/google", tags=["Google Integration"])

# Get the redirect URI from environment or use default
REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/signin")

@router.get("/auth")
async def google_auth():
    """Get Google OAuth URL"""
    try:
        # Create OAuth flow
        flow = google_auth_oauthlib.flow.Flow.from_client_config(
            {
                "web": {
                    "client_id": os.getenv("GOOGLE_CLIENT_ID"),
                    "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [REDIRECT_URI]
                }
            },
            scopes=["openid", "https://www.googleapis.com/auth/userinfo.profile", "https://www.googleapis.com/auth/userinfo.email"]
        )
        
        # Set the redirect URI explicitly
        flow.redirect_uri = REDIRECT_URI
        
        auth_url = flow.authorization_url()[0]
        return {"auth_url": auth_url}
        
    except Exception as e:
        logger.error(f"Error generating auth URL: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error generating auth URL: {str(e)}"
        )

@router.get("/callback")
async def google_callback(request: Request, code: Optional[str] = None):
    """Handle Google OAuth callback"""
    try:
        if not code:
            return RedirectResponse(url="/signin?error=No authorization code provided", status_code=302)

        # Exchange the authorization code for tokens
        token_url = "https://oauth2.googleapis.com/token"
        token_data = {
            "code": code,
            "client_id": os.getenv("GOOGLE_CLIENT_ID"),
            "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
            "redirect_uri": REDIRECT_URI,
            "grant_type": "authorization_code"
        }

        token_response = requests.post(token_url, data=token_data)
        if not token_response.ok:
            logger.error(f"Token exchange failed: {token_response.text}")
            return RedirectResponse(
                url=f"/signin?error=Token exchange failed: {token_response.text}",
                status_code=302
            )

        token_info = token_response.json()
        id_token_str = token_info.get("id_token")

        # Verify the ID token
        client_id = os.getenv("GOOGLE_CLIENT_ID")
        idinfo = id_token.verify_oauth2_token(id_token_str, google_requests.Request(), client_id)
        
        # Create user info
        user = {
            "id": idinfo["sub"],
            "email": idinfo["email"],
            "name": idinfo.get("name"),
            "picture": idinfo.get("picture")
        }
        
        # Store in session
        request.session["user"] = user
        request.session["tokens"] = {
            "access_token": token_info.get("access_token"),
            "refresh_token": token_info.get("refresh_token"),
            "id_token": id_token_str
        }
        
        # Check if client accepts JSON
        accept_header = request.headers.get("accept", "")
        if "application/json" in accept_header:
            return JSONResponse({
                "success": True,
                "user": user,
                "tokens": {
                    "access_token": token_info.get("access_token"),
                    "id_token": id_token_str
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
async def get_google_status(request: Request):
    """Get Google integration status"""
    try:
        # Check if user is authenticated
        user = request.session.get("user")
        if user:
            return {
                "connected": True,
                "email": user["email"],
                "user": user
            }
        return {"connected": False}
    except Exception as e:
        logger.error(f"Error getting Google status: {str(e)}")
        return {"connected": False}