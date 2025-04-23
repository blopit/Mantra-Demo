from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
import os
from datetime import datetime, timedelta
import uuid
import json
import google.oauth2.credentials
import google_auth_oauthlib.flow
from google.oauth2 import id_token
from google.auth.transport import requests
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from oauthlib.oauth2 import WebApplicationClient
import requests as http_requests
from passlib.context import CryptContext

from ...models.google_integration import GoogleIntegration
from ...models.users import Users
from ...utils.database import get_db
# Import helper functions from providers
from src.providers.google.helpers import get_recent_emails, get_user_google_data

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

router = APIRouter(prefix="/api", tags=["google"])

SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile'
]

GOOGLE_OAUTH_TOKEN_URI = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URI = "https://www.googleapis.com/oauth2/v3/userinfo"

async def create_gmail_service(credentials_dict):
    """Create Gmail API service instance"""
    credentials = Credentials(
        token=credentials_dict['token'],
        refresh_token=credentials_dict['refresh_token'],
        token_uri=GOOGLE_OAUTH_TOKEN_URI,
        client_id=os.getenv('GOOGLE_CLIENT_ID'),
        client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
        scopes=SCOPES
    )
    return build('gmail', 'v1', credentials=credentials)

@router.get("/google/data")
async def get_google_data(
    request: Request,
    db: Session = Depends(get_db)
):
    """Get comprehensive Google data for the authenticated user"""
    try:
        # Get user ID from auth header
        user_id = request.headers.get("Authorization")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not authenticated"
            )

        # Get Google integration
        google_integration = db.query(GoogleIntegration).filter(
            GoogleIntegration.user_id == user_id,
            GoogleIntegration.status == 'active'
        ).first()

        if not google_integration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active Google integration found"
            )

        # Fetch all Google data
        data = get_user_google_data(google_integration)

        return {
            'success': True,
            'data': data
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch Google data: {str(e)}"
        )

@router.get("/emails/recent")
async def get_recent_user_emails(
    request: Request,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """Get recent emails for the authenticated user"""
    try:
        # Get user ID from auth header
        user_id = request.headers.get("Authorization")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not authenticated"
            )

        # Fetch recent emails
        try:
            emails = get_recent_emails(db, user_id, limit)
            return {
                'success': True,
                'emails': emails
            }
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch emails: {str(e)}"
        )

@router.post("/google-integrations/disconnect")
async def disconnect_google(
    request: Request,
    db: Session = Depends(get_db)
):
    """Disconnect Google account integration"""
    try:
        # Get user ID from auth header
        user_id = request.headers.get("Authorization")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not authenticated"
            )

        # Find and deactivate the Google integration
        google_integration = db.query(GoogleIntegration).filter(
            GoogleIntegration.user_id == user_id,
            GoogleIntegration.status == 'active'
        ).first()

        if not google_integration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active Google integration found"
            )

        # Update the integration status
        google_integration.status = 'disconnected'
        db.commit()

        return {
            'success': True,
            'message': 'Successfully disconnected Google account'
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Disconnect error: {str(e)}"
        )