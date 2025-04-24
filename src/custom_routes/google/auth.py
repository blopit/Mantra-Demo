"""
Google authentication routes.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from src.utils.database import get_db
from src.models.users import Users
from src.models.google_auth import GoogleAuth
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
import os
import json

router = APIRouter(prefix="/auth/google")

def build_google_oauth():
    """Build Google OAuth flow."""
    client_config = {
        "web": {
            "client_id": os.getenv("GOOGLE_CLIENT_ID"),
            "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [os.getenv("GOOGLE_REDIRECT_URI")],
        }
    }
    flow = Flow.from_client_config(
        client_config,
        scopes=["openid", "https://www.googleapis.com/auth/userinfo.profile", "https://www.googleapis.com/auth/userinfo.email"],
        redirect_uri=os.getenv("GOOGLE_REDIRECT_URI")
    )
    return flow

@router.get("/url")
async def get_auth_url():
    """Get Google OAuth URL."""
    try:
        flow = build_google_oauth()
        authorization_url, state = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true"
        )
        return {"url": authorization_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/callback")
async def auth_callback(request: Request, code: str, state: str, db: Session = Depends(get_db)):
    """Handle Google OAuth callback."""
    try:
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
        db.commit()

        return RedirectResponse(url="/auth/google/store", status_code=303)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/store")
async def store_in_db():
    """Store auth data in database."""
    return RedirectResponse(url="/", status_code=303)

@router.get("/")
async def root():
    """Handle root route."""
    return JSONResponse(content={"message": "Google Auth API"})

@router.get("/status")
async def get_status(db: Session = Depends(get_db)):
    """Get connection status."""
    auth = db.query(GoogleAuth).first()
    if auth:
        user = db.query(Users).filter_by(id=auth.user_id).first()
        return {
            "connected": True,
            "user": {
                "email": user.email,
                "name": user.name,
                "profile_picture": user.profile_picture
            }
        }
    return {"connected": False, "user": None}

@router.post("/disconnect")
async def disconnect(db: Session = Depends(get_db)):
    """Disconnect Google account."""
    auth = db.query(GoogleAuth).first()
    if auth:
        db.delete(auth)
        db.commit()
        return {"message": "Successfully disconnected from Google"}
    raise HTTPException(status_code=404, detail="No Google account connected")


