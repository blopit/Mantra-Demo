"""Gmail Adapter for fetching email data from Gmail API

This adapter connects to the Gmail API and retrieves email data
to be transformed into Tiles.
"""
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
import base64
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .models import GmailMessage, GmailAttachment

logger = logging.getLogger(__name__)

class GmailAdapter:
    """Adapter for Gmail integration"""
    
    REQUIRED_SCOPE = 'https://www.googleapis.com/auth/gmail.readonly'
    
    def __init__(self):
        """Initialize the Gmail adapter"""
        self.service = None
        self.credentials = None
        self.user_email = None
        self._test_mode = os.getenv('TEST_MODE', '').lower() == 'true'
    
    async def connect(self, credentials: Dict[str, Any]) -> bool:
        """Establish connection to Gmail API
        
        Args:
            credentials: Authentication credentials for Gmail API
            
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            if self._test_mode:
                # In test mode, just store the credentials
                self.credentials = credentials
                self.user_email = "test@example.com"
                return True
            
            # Check if Gmail scope is present
            scopes = credentials.get('scopes', [])
            if self.REQUIRED_SCOPE not in scopes:
                logger.error(f"Gmail scope {self.REQUIRED_SCOPE} not present in credentials")
                return False
                
            # Convert dict credentials to Google Credentials object
            creds_obj = Credentials(
                token=credentials.get('access_token'),
                refresh_token=credentials.get('refresh_token'),
                token_uri='https://oauth2.googleapis.com/token',
                client_id=credentials.get('client_id'),
                client_secret=credentials.get('client_secret'),
                scopes=scopes
            )
            
            # Build the Gmail service
            self.service = build('gmail', 'v1', credentials=creds_obj)
            self.credentials = creds_obj
            
            # Get user profile to verify connection
            profile = self.service.users().getProfile(userId='me').execute()
            self.user_email = profile['emailAddress']
            
            logger.info(f"Connected to Gmail as {self.user_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Gmail: {e}")
            return False
    
    async def disconnect(self) -> bool:
        """Disconnect from Gmail API
        
        Returns:
            bool: True if disconnection successful, False otherwise
        """
        # No specific disconnect needed for Gmail API
        self.service = None
        self.credentials = None
        self.user_email = None
        return True
    
    async def fetch_data(self, since: Optional[datetime] = None, limit: int = 50, page_token: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch emails from Gmail
        
        Args:
            since: Fetch emails after this timestamp
            limit: Maximum number of emails to fetch
            page_token: Token for pagination
            
        Returns:
            List[Dict[str, Any]]: List of emails
        """
        if self._test_mode:
            # Return mock data in test mode
            return [
                {
                    'id': 'test_email_1',
                    'threadId': 'thread_1',
                    'from': 'sender@example.com',
                    'to': 'test@example.com',
                    'subject': 'Test Email 1',
                    'body': 'This is a test email body',
                    'date': '2024-04-14T14:39:17Z'
                }
            ]
            
        if not self.service:
            logger.error("Not connected to Gmail API")
            return []
            
        try:
            # Build query for fetching emails
            query = ''
            if since:
                # Format date for Gmail query (RFC 3339 format)
                date_str = since.strftime('%Y/%m/%d')
                query = f'after:{date_str}'
            
            # Get list of message IDs
            result = self.service.users().messages().list(
                userId='me',
                maxResults=limit,
                q=query,
                pageToken=page_token
            ).execute()
            
            messages = result.get('messages', [])
            emails = []
            
            # Fetch details for each message
            for msg in messages:
                try:
                    message = self.service.users().messages().get(
                        userId='me',
                        id=msg['id'],
                        format='full'
                    ).execute()
                    
                    # Extract headers
                    headers = {header['name']: header['value'] 
                              for header in message['payload']['headers']}
                    
                    # Parse email content
                    email_data = self._parse_message(message)
                    emails.append(email_data)
                    
                except Exception as e:
                    logger.warning(f"Error fetching email {msg['id']}: {e}")
                    continue
            
            return emails
            
        except HttpError as e:
            logger.error(f"Gmail API error: {e}")
            return []
        except Exception as e:
            logger.error(f"Error fetching emails: {e}")
            return []
    
    async def push_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Send an email via Gmail
        
        Args:
            data: Email data to send
            
        Returns:
            Dict[str, Any]: Response containing message ID and thread ID
        """
        if self._test_mode:
            # In test mode, return mock response
            return {
                'id': 'test_msg_1',
                'threadId': 'test_thread_1'
            }
            
        if not self.service:
            logger.error("Not connected to Gmail API")
            return {}
            
        try:
            # Create email MIME message
            message = MIMEText(data.get('body', ''))
            message['to'] = data.get('to', '')
            message['subject'] = data.get('subject', '(No subject)')
            
            # Add sender if provided, otherwise use authenticated user
            message['from'] = data.get('from', self.user_email)
            
            # Convert to base64url string
            encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            
            # Send the message
            result = self.service.users().messages().send(
                userId='me',
                body={'raw': encoded_message}
            ).execute()
            
            logger.info(f"Email sent with ID: {result['id']}")
            return result
            
        except HttpError as e:
            logger.error(f"Gmail API error: {e}")
            return {}
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return {}
    
    def _parse_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Gmail message into standardized format
        
        Args:
            message: Raw Gmail message
            
        Returns:
            Dict[str, Any]: Parsed message data
        """
        headers = {header['name']: header['value'] 
                  for header in message['payload']['headers']}
                  
        return {
            'id': message['id'],
            'threadId': message['threadId'],
            'subject': headers.get('Subject', '(No subject)'),
            'from': headers.get('From', ''),
            'to': headers.get('To', ''),
            'date': headers.get('Date', ''),
            'body': self._get_body_content(message['payload']),
            'attachments': self._get_attachments(message['payload'])
        }
    
    def _get_body_content(self, payload: Dict[str, Any]) -> str:
        """Extract email body content
        
        Args:
            payload: Message payload
            
        Returns:
            str: Email body content
        """
        if 'body' in payload and payload['body'].get('data'):
            return base64.urlsafe_b64decode(
                payload['body']['data'].encode('ASCII')
            ).decode('utf-8')
            
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    if 'data' in part['body']:
                        return base64.urlsafe_b64decode(
                            part['body']['data'].encode('ASCII')
                        ).decode('utf-8')
        
        return ''
    
    def _get_attachments(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract attachments from message
        
        Args:
            payload: Message payload
            
        Returns:
            List[Dict[str, Any]]: List of attachment metadata
        """
        attachments = []
        
        if 'parts' not in payload:
            return attachments
            
        for part in payload['parts']:
            if 'filename' in part and part['filename']:
                attachment = {
                    'filename': part['filename'],
                    'mimeType': part['mimeType'],
                    'size': part['body'].get('size', 0),
                    'attachmentId': part['body'].get('attachmentId', '')
                }
                attachments.append(attachment)
                
        return attachments
