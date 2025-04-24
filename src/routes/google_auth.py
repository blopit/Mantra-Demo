from flask import Blueprint, render_template, current_app, url_for, session, request, redirect, jsonify
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import uuid
from src.models.google_integration import GoogleIntegration
from src.models.users import Users
from src.utils.database import SessionLocal
from passlib.context import CryptContext
from src.providers.google.helpers import get_recent_emails, get_user_google_data
import json
import google.oauth2.credentials
import google_auth_oauthlib.flow
from google.oauth2 import id_token
from google.auth.transport import requests
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from oauthlib.oauth2 import WebApplicationClient
import requests as http_requests
import logging

load_dotenv()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

google_auth = Blueprint('google_auth', __name__)

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

async def send_to_webhook(credentials_data: dict, user_info: dict):
    """Send credentials to n8n webhook"""
    webhook_url = os.getenv('WEBHOOK_URL')
    if not webhook_url:
        logging.warning("WEBHOOK_URL not configured")
        return False
        
    try:
        payload = {
            'credentials': credentials_data,
            'user_info': user_info
        }
        response = http_requests.post(webhook_url, json=payload)
        response.raise_for_status()
        return True
    except Exception as e:
        logging.error(f"Failed to send credentials to webhook: {str(e)}")
        return False

@google_auth.route('/')
@google_auth.route('/connect-google')
def connect_google():
    """Render the Google sign-in page"""
    client_id = os.getenv('GOOGLE_CLIENT_ID')
    print(f"Using Google Client ID: {client_id}")  # Debug print

    if not client_id:
        return "Error: GOOGLE_CLIENT_ID not found in environment variables", 500

    # Get user ID from session
    user_id = session.get('user_id')
    google_integration = None

    if user_id:
        db = SessionLocal()
        try:
            google_integration = db.query(GoogleIntegration).filter(
                GoogleIntegration.user_id == user_id,
                GoogleIntegration.status == 'active'
            ).first()
        finally:
            db.close()

    return render_template(
        'google_signin.html',
        google_client_id=client_id,
        user_id=user_id,
        google_integration=google_integration
    )

@google_auth.route('/api/google/callback', methods=['GET', 'POST'])
async def oauth2callback():
    """Handle the Google OAuth2 callback"""
    try:
        # Get the authorization code from query parameters
        code = request.args.get('code')
        if not code:
            return jsonify({'error': 'No authorization code provided'}), 400

        client_id = os.getenv('GOOGLE_CLIENT_ID')
        client_secret = os.getenv('GOOGLE_CLIENT_SECRET')

        # Exchange authorization code for tokens
        token_request_data = {
            'client_id': client_id,
            'client_secret': client_secret,
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': url_for('google_auth.oauth2callback', _external=True)
        }

        token_response = http_requests.post(
            GOOGLE_OAUTH_TOKEN_URI,
            data=token_request_data,
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )

        if not token_response.ok:
            return jsonify({'error': f'Token exchange failed: {token_response.text}'}), 400

        token_data = token_response.json()

        # Get user info using the access token
        userinfo_response = http_requests.get(
            GOOGLE_USERINFO_URI,
            headers={'Authorization': f'Bearer {token_data["access_token"]}'}
        )

        if not userinfo_response.ok:
            return jsonify({'error': 'Failed to get user info'}), 400

        userinfo = userinfo_response.json()
        email = userinfo.get('email')

        if not email:
            return jsonify({'error': 'Email not found in user info'}), 400

        # Check if webhook is requested
        send_to_webhook_enabled = request.args.get('send_to_webhook', 'false').lower() == 'true'
        
        if send_to_webhook_enabled:
            # Prepare credentials data for webhook
            credentials_data = {
                'access_token': token_data['access_token'],
                'refresh_token': token_data.get('refresh_token'),
                'token_uri': GOOGLE_OAUTH_TOKEN_URI,
                'client_id': client_id,
                'client_secret': client_secret,
                'scopes': token_data.get('scope', '').split(' '),
                'expiry': (datetime.utcnow() + timedelta(seconds=token_data.get('expires_in', 3600))).isoformat()
            }
            
            # Send to webhook
            webhook_success = await send_to_webhook(credentials_data, userinfo)
            if not webhook_success:
                logging.warning("Failed to send credentials to webhook")

        db = SessionLocal()
        try:
            # Get or create user
            user = db.query(Users).filter(Users.email == email).first()
            if not user:
                user = Users(
                    email=email,
                    username=f"{userinfo.get('given_name', '')} {userinfo.get('family_name', '')}".strip(),
                    google_id=userinfo['sub'],
                    is_active=True
                )
                db.add(user)
                db.commit()
                db.refresh(user)

            # Create or update Google integration
            google_integration = db.query(GoogleIntegration).filter(
                GoogleIntegration.google_account_id == userinfo['sub']
            ).first()

            expires_at = datetime.utcnow() + timedelta(seconds=token_data.get('expires_in', 3600))

            if not google_integration:
                google_integration = GoogleIntegration(
                    id=str(uuid.uuid4()),
                    user_id=user.id,
                    google_account_id=userinfo['sub'],
                    email=email,
                    access_token=token_data['access_token'],
                    refresh_token=token_data.get('refresh_token'),
                    expires_at=expires_at,
                    scopes=token_data.get('scope', '').split(' '),
                    status='active'
                )
                db.add(google_integration)
            else:
                google_integration.access_token = token_data['access_token']
                if 'refresh_token' in token_data:
                    google_integration.refresh_token = token_data['refresh_token']
                google_integration.expires_at = expires_at
                google_integration.status = 'active'

            db.commit()

            # Store user ID in session
            session['user_id'] = user.id

            # Redirect to emails page
            return redirect('/emails/recent?limit=20')

        except Exception as e:
            db.rollback()
            return jsonify({'error': f'Database error: {str(e)}'}), 500
        finally:
            db.close()

    except Exception as e:
        return jsonify({'error': f'Callback error: {str(e)}'}), 500

@google_auth.route('/api/google-integrations', methods=['POST'])
def store_google_integration():
    """Store Google integration data"""
    try:
        data = request.get_json()
        db = SessionLocal()

        # Get or create user
        user = db.query(Users).filter(Users.email == data['email']).first()
        if not user:
            # Create new user
            user = Users(
                email=data['email'],
                username=f"{data['given_name']} {data['family_name']}".strip(),
                google_id=data['google_account_id'],
                is_active=True
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        # Create or update Google integration
        google_integration = db.query(GoogleIntegration).filter(
            GoogleIntegration.google_account_id == data['google_account_id']
        ).first()

        if not google_integration:
            google_integration = GoogleIntegration(
                id=str(uuid.uuid4()),
                user_id=user.id,
                google_account_id=data['google_account_id'],
                email=data['email'],
                access_token=data['access_token'],
                refresh_token=data['refresh_token'],
                expires_at=datetime.fromisoformat(data['expires_at'].replace('Z', '+00:00')),
                scopes=data['scopes'],
                status=data['status']
            )
            db.add(google_integration)
        else:
            google_integration.access_token = data['access_token']
            google_integration.refresh_token = data['refresh_token']
            google_integration.expires_at = datetime.fromisoformat(data['expires_at'].replace('Z', '+00:00'))
            google_integration.scopes = data['scopes']
            google_integration.status = data['status']

        db.commit()

        # Store user ID in session
        session['user_id'] = user.id

        return jsonify({
            "success": True,
            "email": data['email'],
            "user_id": user.id
        })

    except Exception as e:
        db.rollback()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 400
    finally:
        db.close()

@google_auth.route('/emails/recent', methods=['GET'])
def get_recent_user_emails():
    """Get recent emails for the authenticated user"""
    try:
        db = SessionLocal()

        # Get user ID from session
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'User not authenticated'}), 401

        # Get limit from query params, default to 20
        limit = request.args.get('limit', 20, type=int)

        # Fetch recent emails
        emails = get_recent_emails(db, user_id, limit)

        return jsonify({
            'success': True,
            'emails': emails
        })

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'Failed to fetch emails: {str(e)}'}), 500
    finally:
        db.close()

@google_auth.route('/api/google/disconnect', methods=['POST'])
def disconnect_google():
    """Disconnect Google integration"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'User not authenticated'}), 401

        db = SessionLocal()
        try:
            google_integration = db.query(GoogleIntegration).filter(
                GoogleIntegration.user_id == user_id,
                GoogleIntegration.status == 'active'
            ).first()

            if not google_integration:
                return jsonify({'error': 'No active Google integration found'}), 404

            # Revoke access token with Google
            revoke_response = http_requests.post(
                'https://oauth2.googleapis.com/revoke',
                params={'token': google_integration.access_token},
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )

            # Mark integration as inactive
            google_integration.status = 'inactive'
            google_integration.disconnected_at = datetime.utcnow()
            
            db.commit()

            return jsonify({
                'success': True,
                'message': 'Google integration disconnected successfully'
            })

        except Exception as e:
            db.rollback()
            return jsonify({'error': f'Database error: {str(e)}'}), 500
        finally:
            db.close()

    except Exception as e:
        return jsonify({'error': f'Disconnect error: {str(e)}'}), 500

@google_auth.route('/google/data', methods=['GET'])
def get_google_data():
    """Get comprehensive Google data for the authenticated user"""
    try:
        db = SessionLocal()

        # Get user ID from session
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'User not authenticated'}), 401

        # Get Google integration
        google_integration = db.query(GoogleIntegration).filter(
            GoogleIntegration.user_id == user_id,
            GoogleIntegration.status == 'active'
        ).first()

        if not google_integration:
            return jsonify({'error': 'No active Google integration found'}), 404

        # Fetch all Google data
        data = get_user_google_data(google_integration)

        return jsonify({
            'success': True,
            'data': data
        })

    except Exception as e:
        return jsonify({'error': f'Failed to fetch Google data: {str(e)}'}), 500
    finally:
        db.close()

@google_auth.route('/api/google/refresh-auth')
async def refresh_google_auth():
    """Refresh Google OAuth2 token"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'User not authenticated'}), 401

        db = SessionLocal()
        try:
            google_integration = db.query(GoogleIntegration).filter(
                GoogleIntegration.user_id == user_id,
                GoogleIntegration.status == 'active'
            ).first()

            if not google_integration:
                return jsonify({'error': 'No active Google integration found'}), 404

            if not google_integration.refresh_token:
                return jsonify({'error': 'No refresh token available'}), 400

            # Request new access token using refresh token
            token_request_data = {
                'client_id': os.getenv('GOOGLE_CLIENT_ID'),
                'client_secret': os.getenv('GOOGLE_CLIENT_SECRET'),
                'refresh_token': google_integration.refresh_token,
                'grant_type': 'refresh_token'
            }

            token_response = http_requests.post(
                GOOGLE_OAUTH_TOKEN_URI,
                data=token_request_data,
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )

            if not token_response.ok:
                return jsonify({'error': f'Token refresh failed: {token_response.text}'}), 400

            token_data = token_response.json()

            # Update integration with new access token
            google_integration.access_token = token_data['access_token']
            google_integration.expires_at = datetime.utcnow() + timedelta(seconds=token_data.get('expires_in', 3600))
            
            db.commit()

            return jsonify({'success': True, 'message': 'Token refreshed successfully'})

        except Exception as e:
            db.rollback()
            return jsonify({'error': f'Database error: {str(e)}'}), 500
        finally:
            db.close()

    except Exception as e:
        return jsonify({'error': f'Refresh error: {str(e)}'}), 500