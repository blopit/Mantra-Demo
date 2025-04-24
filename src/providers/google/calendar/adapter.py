"""Google Calendar Adapter for fetching calendar data from Google Calendar API

This adapter connects to the Google Calendar API and retrieves calendar event data
to be transformed into Tiles.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

class CalendarAdapter:
    """Adapter for Google Calendar integration"""
    
    def __init__(self):
        """Initialize the Calendar adapter"""
        self.service = None
        self.credentials = None
        self.user_email = None
    
    async def connect(self, credentials: Dict[str, Any]) -> bool:
        """Establish connection to Google Calendar API
        
        Args:
            credentials: Authentication credentials for Google Calendar API
            
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            # Convert dict credentials to Google Credentials object
            creds_obj = Credentials(
                token=credentials.get('access_token'),
                refresh_token=credentials.get('refresh_token'),
                token_uri='https://oauth2.googleapis.com/token',
                client_id=credentials.get('client_id'),
                client_secret=credentials.get('client_secret'),
                scopes=credentials.get('scopes', ['https://www.googleapis.com/auth/calendar.readonly'])
            )
            
            # Build the Calendar service
            self.service = build('calendar', 'v3', credentials=creds_obj)
            self.credentials = creds_obj
            
            # Get primary calendar to verify connection
            calendar = self.service.calendars().get(calendarId='primary').execute()
            self.user_email = calendar.get('id')
            
            logger.info(f"Connected to Google Calendar as {self.user_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Google Calendar: {e}")
            return False
    
    def disconnect(self) -> bool:
        """Disconnect from Google Calendar API
        
        Returns:
            bool: True if disconnection successful, False otherwise
        """
        # No specific disconnect needed for Google Calendar API
        self.service = None
        self.credentials = None
        self.user_email = None
        return True
    
    def fetch_data(self, since: Optional[datetime] = None, until: Optional[datetime] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Fetch calendar events from Google Calendar
        
        Args:
            since: Fetch events after this timestamp
            until: Fetch events before this timestamp
            limit: Maximum number of events to fetch
            
        Returns:
            List[Dict[str, Any]]: List of calendar events
        """
        if not self.service:
            logger.error("Not connected to Google Calendar API")
            return []
            
        try:
            # Set default time range if not provided
            if not since:
                since = datetime.utcnow()
            if not until:
                until = since + timedelta(days=30)  # Default to 30 days ahead
            
            # Format timestamps for API
            time_min = since.isoformat() + 'Z'  # 'Z' indicates UTC time
            time_max = until.isoformat() + 'Z'
            
            # Get list of events
            events_result = self.service.events().list(
                calendarId='primary',
                timeMin=time_min,
                timeMax=time_max,
                maxResults=limit,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            # Process events into a standardized format
            processed_events = []
            for event in events:
                processed_event = self._process_event(event)
                if processed_event:
                    processed_events.append(processed_event)
            
            return processed_events
            
        except HttpError as e:
            logger.error(f"Google Calendar API error: {e}")
            return []
        except Exception as e:
            logger.error(f"Error fetching calendar events: {e}")
            return []
    
    def push_data(self, data: Dict[str, Any]) -> bool:
        """Create a new calendar event
        
        Args:
            data: Event data to create
            
        Returns:
            bool: True if creation successful, False otherwise
        """
        if not self.service:
            logger.error("Not connected to Google Calendar API")
            return False
            
        try:
            # Create event
            event = {
                'summary': data.get('summary', '(No title)'),
                'location': data.get('location', ''),
                'description': data.get('description', ''),
                'start': {
                    'dateTime': data.get('start_time'),
                    'timeZone': data.get('timezone', 'UTC'),
                },
                'end': {
                    'dateTime': data.get('end_time'),
                    'timeZone': data.get('timezone', 'UTC'),
                },
                'attendees': data.get('attendees', []),
                'reminders': {
                    'useDefault': True
                }
            }
            
            # Add event to calendar
            event = self.service.events().insert(
                calendarId='primary',
                body=event
            ).execute()
            
            logger.info(f"Event created: {event.get('htmlLink')}")
            return True
            
        except HttpError as e:
            logger.error(f"Error creating event: {e}")
            return False
        except Exception as e:
            logger.error(f"Error creating event: {e}")
            return False
    
    async def get_user_info(self) -> Dict[str, Any]:
        """Get user information from Google Calendar
        
        Returns:
            Dict[str, Any]: User profile information
        """
        if not self.service:
            logger.error("Not connected to Google Calendar API")
            return {}
            
        try:
            # Get primary calendar
            calendar = self.service.calendars().get(calendarId='primary').execute()
            
            return {
                'email': calendar.get('id'),
                'summary': calendar.get('summary'),
                'timezone': calendar.get('timeZone')
            }
            
        except Exception as e:
            logger.error(f"Error getting user info: {e}")
            return {}
    
    def setup_webhook(self, webhook_url: str) -> bool:
        """Configure Google Calendar push notifications (if supported)
        
        Args:
            webhook_url: Webhook URL to receive updates
            
        Returns:
            bool: True if webhook setup successful, False otherwise
        """
        # Google Calendar API supports push notifications, but it requires Google Cloud Pub/Sub
        # This is a simplified implementation
        logger.warning("Google Calendar webhook setup is not fully implemented")
        return False
    
    def get_source_metadata(self) -> Dict[str, Any]:
        """Get metadata about Google Calendar
        
        Returns:
            Dict[str, Any]: Metadata about Google Calendar
        """
        return {
            'name': 'Google Calendar',
            'type': 'calendar',
            'features': ['read', 'create', 'update', 'delete'],
            'sync_frequency': 'realtime',
            'icon': 'calendar',
            'supports_reminders': True
        }
    
    def _process_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Process a Google Calendar event into a standardized format
        
        Args:
            event: Raw event from Google Calendar API
            
        Returns:
            Dict[str, Any]: Processed event data
        """
        # Extract start and end times
        start = event.get('start', {})
        end = event.get('end', {})
        
        # Handle all-day events vs. time-specific events
        is_all_day = 'date' in start and 'date' in end
        
        if is_all_day:
            start_time = start.get('date')
            end_time = end.get('date')
        else:
            start_time = start.get('dateTime')
            end_time = end.get('dateTime')
        
        # Extract attendees
        attendees = []
        for attendee in event.get('attendees', []):
            attendees.append({
                'email': attendee.get('email'),
                'name': attendee.get('displayName', ''),
                'response_status': attendee.get('responseStatus', 'needsAction')
            })
        
        # Build processed event
        return {
            'id': event.get('id'),
            'summary': event.get('summary', '(No title)'),
            'description': event.get('description', ''),
            'location': event.get('location', ''),
            'start_time': start_time,
            'end_time': end_time,
            'is_all_day': is_all_day,
            'organizer': event.get('organizer', {}).get('email'),
            'attendees': attendees,
            'html_link': event.get('htmlLink'),
            'status': event.get('status', 'confirmed'),
            'created': event.get('created'),
            'updated': event.get('updated'),
            'recurrence': event.get('recurrence', []),
            'reminders': event.get('reminders', {}).get('overrides', [])
        }
