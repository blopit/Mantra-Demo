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

# Pydantic models for responses
class AuthUrlResponse(BaseModel):
    auth_url: str

class GoogleStatusResponse(BaseModel):
    status: str
    email: Optional[str] = None

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/google", tags=["Google Integration"])

@router.get("/auth", response_model=AuthUrlResponse)
async def google_auth():
    """Generate Google OAuth URL"""
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    redirect_uri = "http://localhost:8000/api/google/callback"
    
    # Google OAuth2 authorization URL with response_type=code for server-side flow
    auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={client_id}&"
        f"redirect_uri={redirect_uri}&"
        "response_type=code&"
        "scope=openid email profile&"
        "access_type=offline&"
        "prompt=consent"
    )
    
    return {"auth_url": auth_url}

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
            "redirect_uri": "http://localhost:8000/api/google/callback",
            "grant_type": "authorization_code"
        }

        token_response = requests.post(token_url, data=token_data)
        if not token_response.ok:
            return RedirectResponse(
                url=f"/signin?error=Token exchange failed: {token_response.text}",
                status_code=302
            )

        token_info = token_response.json()
        id_token_str = token_info.get("id_token")

        # Verify the ID token
        client_id = os.getenv("GOOGLE_CLIENT_ID")
        idinfo = id_token.verify_oauth2_token(id_token_str, google_requests.Request(), client_id)
        
        # Store user info and tokens in session or secure storage
        request.session["user"] = {
            "id": idinfo["sub"],
            "email": idinfo["email"],
            "name": idinfo.get("name"),
            "picture": idinfo.get("picture")
        }
        request.session["tokens"] = {
            "access_token": token_info.get("access_token"),
            "refresh_token": token_info.get("refresh_token"),
            "id_token": id_token_str
        }
        
        # Redirect to accounts page
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
                "status": "success",
                "email": user["email"]
            }
        return {"status": "not_authenticated"}
    except Exception as e:
        logger.error(f"Error getting Google status: {str(e)}")
        return {"status": "error"}