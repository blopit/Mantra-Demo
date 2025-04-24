"""
Gmail service for Ultimate Assistant.
Handles fetching and processing email data from Gmail API.
"""

import base64
import logging
import os
import re
import traceback
from typing import Dict, List, Any, Optional
from bs4 import BeautifulSoup
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from googleapiclient.errors import HttpError
from datetime import datetime, timezone
from googleapiclient.http import build_http
from google.auth.transport.requests import Request
from email.mime.text import MIMEText
from fastapi import HTTPException

from ..auth import GoogleAuthManager

logger = logging.getLogger(__name__)

class GmailService:
    """Service class for Gmail API interactions"""

    def __init__(self, db=None):
        """Initialize Gmail service without connecting"""
        self.service = None
        self.credentials = None
        self.auth_manager = GoogleAuthManager(db) if db else None
        logger.info("Gmail service initialized (not connected)")

    async def handle_auth_error(self, error: Exception, user_id: str) -> None:
        """
        Handle authentication errors by clearing credentials and raising appropriate exception
        """
        error_str = str(error).lower()
        if "invalid_grant" in error_str or "token has been expired or revoked" in error_str:
            logger.warning(f"Auth token invalid/expired for user {user_id}, clearing credentials")
            try:
                # Get the credentials first - properly await the coroutine
                credentials = await self.auth_manager.get_credentials(user_id)
                if credentials:
                    # Properly await the clear_credentials coroutine
                    await self.auth_manager.clear_credentials(credentials)
            except Exception as e:
                logger.error(f"Error clearing credentials: {e}")
            
            # Raise 401 to trigger re-authentication
            raise HTTPException(
                status_code=401,
                detail="Authentication expired. Please re-authenticate.",
                headers={"X-Redirect": "/api/google/refresh-auth"}
            )
        raise error

    async def connect(self, credentials: Dict[str, Any]) -> bool:
        """Connect to Gmail API with credentials"""
        try:
            # Build credentials object
            creds = Credentials(
                token=credentials.get('access_token'),
                refresh_token=credentials.get('refresh_token'),
                token_uri=credentials.get('token_uri'),
                client_id=credentials.get('client_id'),
                client_secret=credentials.get('client_secret'),
                scopes=credentials.get('scopes')
            )
            
            # Check if credentials are expired
            if creds.expired:
                logger.info("Credentials expired, attempting refresh")
                try:
                    creds.refresh(Request())
                    logger.info("Successfully refreshed credentials")
                    
                    # Update stored credentials with new access token
                    credentials['access_token'] = creds.token
                    if creds.expiry:
                        credentials['expiry'] = int(creds.expiry.timestamp())
                    
                    # Save the updated credentials
                    await self.auth_manager.save_credentials(credentials.get('user_id'), credentials)
                except Exception as e:
                    logger.error(f"Failed to refresh credentials: {e}")
                    logger.debug("Error traceback:", exc_info=True)
                    await self.handle_auth_error(e, credentials.get('user_id'))
                    return False
            
            # Build Gmail service
            try:
                logger.debug("Building Gmail service...")
                self.service = build('gmail', 'v1', credentials=creds)
                logger.info("Successfully built Gmail service")
                
                # Test connection by getting user profile
                try:
                    profile = self.service.users().getProfile(userId='me').execute()
                    if profile and 'emailAddress' in profile:
                        logger.info(f"Connected to Gmail for {profile['emailAddress']}")
                        return True
                    else:
                        logger.error("Could not get user profile")
                        return False
                except Exception as e:
                    logger.error(f"Error getting user profile: {e}")
                    logger.debug("Error traceback:", exc_info=True)
                    await self.handle_auth_error(e, credentials.get('user_id'))
                    return False
                
            except Exception as e:
                logger.error(f"Error building Gmail service: {e}")
                logger.debug("Error traceback:", exc_info=True)
                await self.handle_auth_error(e, credentials.get('user_id'))
                return False
            
        except Exception as e:
            logger.error(f"Error connecting to Gmail: {e}")
            logger.debug("Error traceback:", exc_info=True)
            await self.handle_auth_error(e, credentials.get('user_id'))
            return False

    async def get_profile(self, user_id: str = 'me') -> Optional[Dict[str, Any]]:
        """Get Gmail user profile"""
        if not self.service:
            logger.error("Gmail service not initialized")
            return None

        try:
            logger.debug("Getting Gmail user profile...")
            profile = self.service.users().getProfile(userId=user_id).execute()

            if profile:
                logger.info(f"Successfully got profile for {profile.get('emailAddress')}")
                return profile
            else:
                logger.warning("No profile data returned")
                return None

        except Exception as e:
            logger.error(f"Error getting Gmail profile: {str(e)}")
            logger.debug("Error traceback:", exc_info=True)
            return None

    async def get_messages(self,
                    user_id: str = 'me',
                    max_results: int = 20,
                    query: str = None) -> List[Dict[str, Any]]:
        """Fetch messages from Gmail"""
        if not self.service:
            logger.error("Gmail service not initialized")
            return []

        try:
            # Build the query
            query_params = {
                'userId': user_id,
                'maxResults': max_results,
                'labelIds': ['INBOX']  # Only fetch from inbox
            }

            if query:
                query_params['q'] = query

            logger.debug(f"Gmail API query parameters: {query_params}")

            # List messages
            try:
                logger.debug("Making Gmail API list request...")
                results = self.service.users().messages().list(**query_params).execute()
                logger.debug(f"Gmail API list response: {results}")

                messages = results.get('messages', [])
                logger.info(f"Found {len(messages)} messages in Gmail")

                if not messages:
                    logger.info("No messages found in Gmail")
                    # Check if we have any other labels available
                    labels = self.service.users().labels().list(userId=user_id).execute()
                    logger.debug(f"Available labels: {labels}")
                    return []

                # Fetch full details for each message
                detailed_messages = []
                for message in messages:
                    try:
                        msg_id = message['id']
                        logger.debug(f"Fetching details for message {msg_id}...")

                        # Get the full message with complete payload
                        msg_details = self.service.users().messages().get(
                            userId=user_id,
                            id=msg_id,
                            format='full'  # Ensure we get the full message format
                        ).execute()

                        if msg_details:
                            logger.info(f"Successfully fetched details for message {msg_id}")
                            detailed_messages.append(msg_details)
                        else:
                            logger.warning(f"No details found for message {msg_id}")
                    except Exception as e:
                        logger.error(f"Error fetching details for message {msg_id}: {e}")
                        logger.debug("Error traceback:", exc_info=True)
                        continue

                logger.info(f"Successfully fetched details for {len(detailed_messages)} messages")
                return detailed_messages

            except Exception as e:
                logger.error(f"Error listing Gmail messages: {e}")
                logger.debug("Error traceback:", exc_info=True)
                return []

        except Exception as e:
            logger.error(f"Error fetching Gmail messages: {e}")
            logger.debug("Error traceback:", exc_info=True)
            return []

    def _process_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process raw message into structured format

        Args:
            message: Raw message from Gmail API

        Returns:
            Processed message or None if invalid
        """
        try:
            if not message or 'payload' not in message:
                logger.warning("Invalid message format - missing payload")
                return None

            # Extract headers
            headers = message['payload'].get('headers', [])
            header_data = {
                'subject': '',
                'from': '',
                'to': '',
                'date': None
            }

            for header in headers:
                name = header.get('name', '').lower()
                if name in header_data:
                    header_data[name] = header.get('value', '')

            # Get message body
            body = self._get_message_body(message['payload'])
            if not body:
                logger.warning(f"No readable body found for message {message['id']}")
                body = "No content available"

            # Convert date string to datetime
            try:
                date = datetime.strptime(header_data['date'], "%a, %d %b %Y %H:%M:%S %z")
            except (ValueError, TypeError) as e:
                logger.warning(f"Error parsing date {header_data['date']}: {e}")
                date = datetime.now(timezone.utc)

            # Build processed message
            processed_msg = {
                'id': message['id'],
                'thread_id': message.get('threadId', ''),
                'title': header_data['subject'],
                'content': body,
                'from': header_data['from'],
                'to': header_data['to'],
                'date': date,
                'labels': message.get('labelIds', []),
                'snippet': message.get('snippet', ''),
                'platform_specific_data': {
                    'source_id': message['id'],
                    'thread_id': message.get('threadId', ''),
                    'labels': message.get('labelIds', []),
                    'flags': {
                        'unread': 'UNREAD' in message.get('labelIds', []),
                        'important': 'IMPORTANT' in message.get('labelIds', []),
                        'starred': 'STARRED' in message.get('labelIds', []),
                        'spam': 'SPAM' in message.get('labelIds', []),
                        'trash': 'TRASH' in message.get('labelIds', [])
                    }
                }
            }

            return processed_msg

        except Exception as e:
            logger.error(f"Error processing message {message.get('id', 'unknown')}: {e}")
            logger.debug(traceback.format_exc())
            return None

    def _clean_html_content(self, html_content: str) -> str:
        """
        Extract readable text from HTML content, removing formatting and clutter

        Args:
            html_content: HTML string

        Returns:
            Clean text content
        """
        try:
            # Parse HTML with BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')

            # Remove script and style elements
            for element in soup(['script', 'style']):
                element.decompose()

            # Remove email quotes and signatures
            for element in soup.find_all(['blockquote', 'div']):
                classes = element.get('class', [])
                if any(c in str(classes).lower() for c in ['quote', 'signature', 'gmail_quote']):
                    element.decompose()

            # Get text content
            text = soup.get_text()

            # Clean up whitespace and formatting
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            text = ' '.join(lines)

            # Remove common email markers
            text = re.sub(r'On.*wrote:.*$', '', text, flags=re.MULTILINE)
            text = re.sub(r'^>.*$', '', text, flags=re.MULTILINE)

            # Limit length for processing
            if len(text) > 1000:
                text = text[:997] + '...'

            return text.strip()

        except Exception as e:
            logger.error(f"Error cleaning HTML content: {e}")
            return html_content[:1000]  # Fallback to truncated original

    def _get_message_body(self, payload: Dict[str, Any]) -> str:
        """
        Extract message body from payload, preferring plain text over HTML

        Args:
            payload: Message payload from Gmail API

        Returns:
            Message body text
        """
        try:
            # First try to get plain text content
            if 'body' in payload and payload['body'].get('data'):
                if payload.get('mimeType') == 'text/plain':
                    return self._decode_body(payload['body'])

            # Check parts for plain text
            if 'parts' in payload:
                # First pass - look only for text/plain
                for part in payload['parts']:
                    if part.get('mimeType') == 'text/plain':
                        body = self._decode_body(part['body'])
                        if body:
                            return body

                # Second pass - if no plain text, try HTML as fallback
                for part in payload['parts']:
                    if part.get('mimeType') == 'text/html':
                        html_body = self._decode_body(part['body'])
                        if html_body:
                            return self._clean_html_content(html_body)

                    # Check nested parts
                    if 'parts' in part:
                        for nested_part in part['parts']:
                            if nested_part.get('mimeType') == 'text/plain':
                                body = self._decode_body(nested_part['body'])
                                if body:
                                    return body

            # If nothing else found, try HTML content from body
            if 'body' in payload and payload['body'].get('data'):
                if payload.get('mimeType') == 'text/html':
                    html_body = self._decode_body(payload['body'])
                    if html_body:
                        return self._clean_html_content(html_body)

            return ''

        except Exception as e:
            logger.error(f"Error extracting message body: {e}")
            logger.debug(traceback.format_exc())
            return ''

    def _decode_body(self, body: Dict[str, Any]) -> str:
        """
        Decode message body from base64

        Args:
            body: Message body from Gmail API

        Returns:
            Decoded body text
        """
        try:
            if 'data' not in body:
                return ''

            # Decode base64
            text = base64.urlsafe_b64decode(body['data']).decode()

            # Clean up text
            text = text.replace('\r\n', '\n').strip()

            return text

        except Exception as e:
            logger.error(f"Error decoding message body: {e}")
            logger.debug(traceback.format_exc())
            return ''

    async def list_messages(self, limit: int = 20) -> Optional[Dict[str, Any]]:
        """List recent messages"""
        if not self.service:
            return None

        try:
            return self.service.users().messages().list(userId='me', maxResults=limit).execute()
        except HttpError as e:
            logger.error(f"Error listing messages: {str(e)}")
            return None

    async def get_message(self, message_id: str, user_id: str = 'me') -> Optional[Dict[str, Any]]:
        """Get a specific message by ID"""
        if not self.service:
            logger.error("Gmail service not initialized")
            return None

        try:
            logger.debug(f"Fetching message {message_id}...")
            message = self.service.users().messages().get(
                userId=user_id,
                id=message_id,
                format='full'
            ).execute()

            if message:
                logger.info(f"Successfully fetched message {message_id}")
                return message
            else:
                logger.warning(f"No message found with ID {message_id}")
                return None

        except Exception as e:
            logger.error(f"Error getting message {message_id}: {str(e)}")
            logger.debug("Error traceback:", exc_info=True)
            return None

    def _get_attachments(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get attachments from message payload"""
        attachments = []

        def process_parts(part):
            if 'filename' in part and part['filename']:
                attachments.append({
                    'id': part.get('body', {}).get('attachmentId'),
                    'filename': part['filename'],
                    'mimeType': part['mimeType']
                })
            if 'parts' in part:
                for p in part['parts']:
                    process_parts(p)

        if 'parts' in payload:
            for part in payload['parts']:
                process_parts(part)

        return attachments

    async def send_message(self,
                       to: str,
                       subject: str,
                       body: str,
                       thread_id: str = None,
                       user_id: str = 'me') -> Optional[Dict[str, Any]]:
        """Send an email message"""
        if not self.service:
            logger.error("Gmail service not initialized")
            return None

        try:
            # Create message
            message = MIMEText(body)
            message['to'] = to
            message['subject'] = subject

            # Encode the message
            raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

            # Prepare the message for sending
            body = {'raw': raw}
            if thread_id:
                body['threadId'] = thread_id

            logger.debug(f"Sending email to {to} with subject: {subject}")

            # Send the message
            try:
                sent_message = self.service.users().messages().send(
                    userId=user_id,
                    body=body
                ).execute()

                if sent_message:
                    logger.info(f"Successfully sent message with ID: {sent_message.get('id')}")
                    return sent_message
                else:
                    logger.warning("Message sent but no response received")
                    return None

            except Exception as e:
                logger.error(f"Error sending message: {str(e)}")
                logger.debug("Error traceback:", exc_info=True)
                return None

        except Exception as e:
            logger.error(f"Error preparing message: {str(e)}")
            logger.debug("Error traceback:", exc_info=True)
            return None
