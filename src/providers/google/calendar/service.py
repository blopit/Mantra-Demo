"""
Google Calendar service for Ultimate Assistant.
Handles fetching and processing calendar data from Google Calendar API.
"""

import logging
import traceback
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request
from fastapi import HTTPException

from ..auth import GoogleAuthManager

logger = logging.getLogger(__name__)

class CalendarService:
    """Service class for Google Calendar API interactions"""
    
    def __init__(self):
        """Initialize Calendar service without connecting"""
        self.service = None
        self.credentials = None
        self.auth_manager = GoogleAuthManager()
        logger.info("Google Calendar service initialized (not connected)")

    async def handle_auth_error(self, error: Exception, user_id: str) -> None:
        """
        Handle authentication errors by clearing credentials and raising appropriate exception
        """
        error_str = str(error).lower()
        if "invalid_grant" in error_str or "token has been expired or revoked" in error_str:
            logger.warning(f"Auth token invalid/expired for user {user_id}, clearing credentials")
            await self.auth_manager.clear_credentials(user_id)
            raise HTTPException(
                status_code=401,
                detail="Authentication expired. Please re-authenticate.",
                headers={"X-Redirect": "/api/google/refresh-auth"}
            )
        raise error

    async def connect(self, credentials: Dict[str, Any]) -> bool:
        """Connect to Google Calendar API with credentials"""
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
                except Exception as e:
                    logger.error(f"Failed to refresh credentials: {e}")
                    logger.debug("Error traceback:", exc_info=True)
                    await self.handle_auth_error(e, credentials.get('user_id'))
                    return False
            
            # Build Calendar service
            try:
                logger.debug("Building Google Calendar service...")
                self.service = build('calendar', 'v3', credentials=creds)
                logger.info("Successfully built Google Calendar service")
                
                # Test connection by getting primary calendar
                try:
                    calendar = self.service.calendars().get(calendarId='primary').execute()
                    if calendar and 'id' in calendar:
                        logger.info(f"Connected to Google Calendar for {calendar['id']}")
                        return True
                    else:
                        logger.error("Could not get primary calendar")
                        return False
                except Exception as e:
                    logger.error(f"Error getting primary calendar: {e}")
                    logger.debug("Error traceback:", exc_info=True)
                    await self.handle_auth_error(e, credentials.get('user_id'))
                    return False
                    
            except Exception as e:
                logger.error(f"Error building Google Calendar service: {e}")
                logger.debug("Error traceback:", exc_info=True)
                await self.handle_auth_error(e, credentials.get('user_id'))
                return False
                
        except Exception as e:
            logger.error(f"Error connecting to Google Calendar: {e}")
            logger.debug("Error traceback:", exc_info=True)
            await self.handle_auth_error(e, credentials.get('user_id'))
            return False

    async def get_calendars(self) -> List[Dict[str, Any]]:
        """Get list of user's calendars"""
        if not self.service:
            logger.error("Google Calendar service not initialized")
            return []
            
        try:
            logger.debug("Getting user's calendars...")
            calendar_list = self.service.calendarList().list().execute()
            
            if calendar_list and 'items' in calendar_list:
                calendars = calendar_list['items']
                logger.info(f"Successfully retrieved {len(calendars)} calendars")
                return calendars
            else:
                logger.warning("No calendars found")
                return []
                
        except Exception as e:
            logger.error(f"Error getting calendars: {str(e)}")
            logger.debug("Error traceback:", exc_info=True)
            return []

    async def get_events(self, 
                    calendar_id: str = 'primary',
                    days_ahead: int = 30,
                    max_results: int = 50) -> List[Dict[str, Any]]:
        """Fetch upcoming events from Google Calendar"""
        if not self.service:
            logger.error("Google Calendar service not initialized")
            return []
            
        try:
            # Calculate time range
            now = datetime.utcnow()
            time_min = now.isoformat() + 'Z'  # 'Z' indicates UTC time
            time_max = (now + timedelta(days=days_ahead)).isoformat() + 'Z'
            
            logger.debug(f"Fetching events from {time_min} to {time_max}")
            
            # Get events
            events_result = self.service.events().list(
                calendarId=calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            logger.info(f"Found {len(events)} upcoming events")
            
            # Process events
            processed_events = []
            for event in events:
                try:
                    processed_event = self._process_event(event)
                    processed_events.append(processed_event)
                except Exception as e:
                    logger.error(f"Error processing event {event.get('id')}: {e}")
                    continue
            
            return processed_events
            
        except Exception as e:
            logger.error(f"Error fetching events: {str(e)}")
            logger.debug("Error traceback:", exc_info=True)
            return []

    def _process_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Process a calendar event into a standardized format"""
        # Extract start and end times
        start = event.get('start', {})
        end = event.get('end', {})
        
        # Handle all-day events vs. time-specific events
        is_all_day = 'date' in start and 'date' in end
        
        # Format start and end times
        if is_all_day:
            start_time = start.get('date')
            end_time = end.get('date')
            start_display = start_time
            end_display = end_time
        else:
            start_time = start.get('dateTime')
            end_time = end.get('dateTime')
            # Format for display
            try:
                start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                start_display = start_dt.strftime('%Y-%m-%d %H:%M')
                end_display = end_dt.strftime('%H:%M') if start_dt.date() == end_dt.date() else end_dt.strftime('%Y-%m-%d %H:%M')
            except Exception:
                start_display = start_time
                end_display = end_time
        
        # Extract attendees
        attendees = []
        for attendee in event.get('attendees', []):
            attendees.append({
                'email': attendee.get('email'),
                'name': attendee.get('displayName', ''),
                'response_status': attendee.get('responseStatus', 'needsAction'),
                'optional': attendee.get('optional', False)
            })
        
        # Build processed event
        return {
            'id': event.get('id'),
            'title': event.get('summary', '(No title)'),
            'description': event.get('description', ''),
            'location': event.get('location', ''),
            'start': {
                'datetime': start_time,
                'timezone': start.get('timeZone', 'UTC'),
                'display': start_display
            },
            'end': {
                'datetime': end_time,
                'timezone': end.get('timeZone', 'UTC'),
                'display': end_display
            },
            'is_all_day': is_all_day,
            'organizer': event.get('organizer', {}).get('email'),
            'creator': event.get('creator', {}).get('email'),
            'attendees': attendees,
            'link': event.get('htmlLink', ''),
            'status': event.get('status', 'confirmed'),
            'created': event.get('created'),
            'updated': event.get('updated'),
            'recurrence': event.get('recurrence', []),
            'conference_data': event.get('conferenceData', {}),
            'reminders': event.get('reminders', {}).get('overrides', [])
        }

    async def create_event(self, 
                       summary: str, 
                       start_time: str,
                       end_time: str,
                       description: str = '',
                       location: str = '',
                       attendees: List[Dict[str, str]] = None,
                       calendar_id: str = 'primary') -> Optional[Dict[str, Any]]:
        """Create a new calendar event"""
        if not self.service:
            logger.error("Google Calendar service not initialized")
            return None
            
        try:
            # Create event body
            event = {
                'summary': summary,
                'location': location,
                'description': description,
                'start': {
                    'dateTime': start_time,
                    'timeZone': 'UTC',
                },
                'end': {
                    'dateTime': end_time,
                    'timeZone': 'UTC',
                },
                'reminders': {
                    'useDefault': True
                }
            }
            
            # Add attendees if provided
            if attendees:
                event['attendees'] = attendees
            
            # Create the event
            created_event = self.service.events().insert(
                calendarId=calendar_id,
                body=event,
                sendUpdates='all'  # Send notifications to attendees
            ).execute()
            
            if created_event:
                logger.info(f"Successfully created event: {created_event.get('htmlLink')}")
                return created_event
            else:
                logger.warning("Event created but no response received")
                return None
                
        except Exception as e:
            logger.error(f"Error creating event: {str(e)}")
            logger.debug("Error traceback:", exc_info=True)
            return None

    async def update_event(self,
                       event_id: str,
                       summary: Optional[str] = None,
                       start_time: Optional[str] = None,
                       end_time: Optional[str] = None,
                       description: Optional[str] = None,
                       location: Optional[str] = None,
                       attendees: Optional[List[Dict[str, str]]] = None,
                       calendar_id: str = 'primary') -> Optional[Dict[str, Any]]:
        """Update an existing calendar event"""
        if not self.service:
            logger.error("Google Calendar service not initialized")
            return None
            
        try:
            # Get the existing event
            event = self.service.events().get(
                calendarId=calendar_id,
                eventId=event_id
            ).execute()
            
            # Update fields if provided
            if summary:
                event['summary'] = summary
            if description:
                event['description'] = description
            if location:
                event['location'] = location
            
            # Update start time if provided
            if start_time:
                if 'dateTime' in event['start']:
                    event['start']['dateTime'] = start_time
                else:
                    # Convert from all-day to timed event
                    event['start'] = {
                        'dateTime': start_time,
                        'timeZone': 'UTC'
                    }
            
            # Update end time if provided
            if end_time:
                if 'dateTime' in event['end']:
                    event['end']['dateTime'] = end_time
                else:
                    # Convert from all-day to timed event
                    event['end'] = {
                        'dateTime': end_time,
                        'timeZone': 'UTC'
                    }
            
            # Update attendees if provided
            if attendees:
                event['attendees'] = attendees
            
            # Update the event
            updated_event = self.service.events().update(
                calendarId=calendar_id,
                eventId=event_id,
                body=event,
                sendUpdates='all'  # Send notifications to attendees
            ).execute()
            
            if updated_event:
                logger.info(f"Successfully updated event: {updated_event.get('htmlLink')}")
                return updated_event
            else:
                logger.warning("Event updated but no response received")
                return None
                
        except Exception as e:
            logger.error(f"Error updating event: {str(e)}")
            logger.debug("Error traceback:", exc_info=True)
            return None

    async def delete_event(self, event_id: str, calendar_id: str = 'primary') -> bool:
        """Delete a calendar event"""
        if not self.service:
            logger.error("Google Calendar service not initialized")
            return False
            
        try:
            # Delete the event
            self.service.events().delete(
                calendarId=calendar_id,
                eventId=event_id,
                sendUpdates='all'  # Send notifications to attendees
            ).execute()
            
            logger.info(f"Successfully deleted event {event_id}")
            return True
                
        except Exception as e:
            logger.error(f"Error deleting event: {str(e)}")
            logger.debug("Error traceback:", exc_info=True)
            return False
