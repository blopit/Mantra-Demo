"""
Service for transforming data into tiles.

This module provides functionality to transform various types of data
(emails, calendar events, etc.) into a standardized tile format.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
from pydantic import BaseModel

from src.schemas.google import Tile, RelatedEvent

logger = logging.getLogger(__name__)

class TransformationService:
    """Service for transforming data into tiles."""
    
    def transform_to_tiles(self, data: List[Dict[str, Any]], data_type: str) -> List[Tile]:
        """Transform data into tiles.
        
        Args:
            data: List of data items to transform
            data_type: Type of data ('email', 'calendar', etc.)
            
        Returns:
            List[Tile]: List of transformed tiles
        """
        if not data:
            logger.warning(f"No data provided for transformation of type: {data_type}")
            return []
            
        try:
            # Select appropriate transformer based on data type
            transformer = self._get_transformer(data_type)
            if not transformer:
                logger.error(f"No transformer found for data type: {data_type}")
                return []
                
            # Transform each item
            tiles = []
            for item in data:
                try:
                    tile = transformer(item)
                    if tile:
                        tiles.append(tile)
                except Exception as e:
                    logger.error(f"Error transforming item: {str(e)}")
                    continue
                    
            return tiles
            
        except Exception as e:
            logger.error(f"Error in transform_to_tiles: {str(e)}")
            return []
    
    def _get_transformer(self, data_type: str):
        """Get the appropriate transformer function for the data type.
        
        Args:
            data_type: Type of data to transform
            
        Returns:
            Callable: Transformer function
        """
        transformers = {
            'email': self._transform_email,
            'calendar': self._transform_calendar_event
        }
        return transformers.get(data_type.lower())
    
    def _transform_email(self, email: Dict[str, Any]) -> Optional[Tile]:
        """Transform an email into a tile.
        
        Args:
            email: Email data to transform
            
        Returns:
            Optional[Tile]: Transformed tile or None if transformation fails
        """
        try:
            # Extract basic email data
            title = email.get('title', 'No Subject')
            content = email.get('content', '')
            sender = email.get('from', 'Unknown Sender')
            date = email.get('date')
            
            # Create tile
            tile = Tile(
                id=email.get('id', ''),
                title=title,
                content=content,
                source="gmail",
                source_id=email.get('platform_specific_data', {}).get('source_id', ''),
                created_at=date,
                updated_at=date,
                metadata={
                    'sender': sender,
                    'recipients': email.get('to', []),
                    'labels': email.get('platform_specific_data', {}).get('labels', []),
                    'flags': email.get('platform_specific_data', {}).get('flags', {}),
                    'thread_id': email.get('platform_specific_data', {}).get('thread_id', '')
                }
            )
            
            return tile
            
        except Exception as e:
            logger.error(f"Error transforming email: {str(e)}")
            return None
    
    def _transform_calendar_event(self, event: Dict[str, Any]) -> Optional[Tile]:
        """Transform a calendar event into a tile.
        
        Args:
            event: Calendar event data to transform
            
        Returns:
            Optional[Tile]: Transformed tile or None if transformation fails
        """
        try:
            # Extract basic event data
            title = event.get('summary', 'Untitled Event')
            description = event.get('description', '')
            start_time = event.get('start', {}).get('dateTime') or event.get('start', {}).get('date')
            end_time = event.get('end', {}).get('dateTime') or event.get('end', {}).get('date')
            
            # Create related event
            related_event = RelatedEvent(
                id=event.get('id', ''),
                title=title,
                start_time=start_time,
                end_time=end_time,
                location=event.get('location', ''),
                attendees=[
                    attendee.get('email', '')
                    for attendee in event.get('attendees', [])
                ]
            )
            
            # Create tile
            tile = Tile(
                id=event.get('id', ''),
                title=title,
                content=description,
                source="google_calendar",
                source_id=event.get('id', ''),
                created_at=event.get('created'),
                updated_at=event.get('updated'),
                metadata={
                    'calendar_id': event.get('calendar_id', ''),
                    'organizer': event.get('organizer', {}).get('email', ''),
                    'status': event.get('status', ''),
                    'is_recurring': bool(event.get('recurrence', [])),
                    'video_conference': event.get('hangoutLink') or event.get('conferenceData', {}).get('entryPoints', [{}])[0].get('uri', '')
                },
                related_events=[related_event]
            )
            
            return tile
            
        except Exception as e:
            logger.error(f"Error transforming calendar event: {str(e)}")
            return None 