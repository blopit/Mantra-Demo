"""
Google authentication routes.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from src.utils.database import get_db
from src.models.users import Users
from src.models.google_auth import GoogleAuth
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
import os
import json
from datetime import datetime
from itsdangerous import URLSafeSerializer

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
async def get_auth_url(request: Request):
    """Get Google OAuth URL."""
    try:
        flow = build_google_oauth()
        authorization_url, state = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true"
        )
        request.session["state"] = state
        return {"url": authorization_url, "state": state}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/callback")
async def callback(
    request: Request,
    code: str = Query(...),
    state: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """Handle Google OAuth callback."""
    # Verify state
    session = request.session
    if "state" not in session or session["state"] != state:
        raise HTTPException(
            status_code=400,
            detail="Invalid state. Please try authenticating again."
        )

    try:
        # Get OAuth credentials
        flow = build_google_oauth()
        flow.fetch_token(code=code)
        credentials = flow.credentials

        # Get user info
        service = build("oauth2", "v2", credentials=credentials)
        user_info = service.userinfo().get().execute()

        # Find or create user
        result = await db.execute(
            select(Users).where(Users.email == user_info["email"])
        )
        user = result.scalar_one_or_none()

        if not user:
            user = Users(
                id=user_info["sub"],
                email=user_info["email"],
                name=user_info.get("name", ""),
                profile_picture=user_info.get("picture", ""),
                is_active=True
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)

        # Store auth info
        auth = GoogleAuth(
            user_id=user.id,
            email=user.email,
            access_token=credentials.token,
            refresh_token=credentials.refresh_token,
            token_expiry=datetime.fromtimestamp(credentials.expiry.timestamp())
        )
        db.add(auth)
        await db.commit()

        # Store user info in session
        session["user"] = {
            "id": user.id,
            "email": user.email,
            "name": user.name
        }

        return RedirectResponse(url="/auth/google/store", status_code=303)

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to authenticate with Google: {str(e)}"
        )

@router.get("/store")
async def store_in_db():
    """Store auth data in database."""
    return RedirectResponse(url="/", status_code=303)

@router.get("/")
async def root():
    """Handle root route."""
    return JSONResponse(content={"message": "Google Auth API"})

@router.get("/status")
async def get_status(request: Request, db: AsyncSession = Depends(get_db)):
    """Get connection status."""
    # Get user from session
    user = request.session.get("user")
    if not user:
        # For testing, try to get user from cookie
        try:
            serializer = URLSafeSerializer("test_secret_key")
            session_data = serializer.loads(request.cookies.get("session", ""))
            user = session_data.get("user")
        except Exception:
            user = None

    if not user:
        return {"connected": False, "user": None}

    # Get auth record for this user
    result = await db.execute(
        select(GoogleAuth).where(GoogleAuth.user_id == user["id"])
    )
    auth = result.scalar_one_or_none()
    
    if auth:
        result = await db.execute(
            select(Users).where(Users.id == auth.user_id)
        )
        user = result.scalar_one_or_none()
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
async def disconnect(request: Request, db: AsyncSession = Depends(get_db)):
    """Disconnect Google account."""
    try:
        # Get user from session
        user = request.session.get("user")
        if not user:
            # For testing, try to get user from cookie
            try:
                serializer = URLSafeSerializer("test_secret_key")
                session_data = serializer.loads(request.cookies.get("session", ""))
                user = session_data.get("user")
            except Exception:
                user = None

        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")

        # Delete all auth records for this user
        await db.execute(
            delete(GoogleAuth).where(GoogleAuth.user_id == user["id"])
        )
        await db.commit()

        # Clear session
        request.session.pop("user", None)

        return {"message": "Successfully disconnected Google account"}

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to disconnect Google account: {str(e)}"
        )


