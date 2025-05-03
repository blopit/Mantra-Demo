"""
Schemas for Google-related data structures.

This module defines Pydantic models for Google data structures,
particularly for tiles and related events.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class RelatedEvent(BaseModel):
    """Model for events related to a tile."""
    
    id: str = Field(..., description="Unique identifier for the event")
    title: str = Field(..., description="Title of the event")
    start_time: str = Field(..., description="Start time of the event")
    end_time: str = Field(..., description="End time of the event")
    location: Optional[str] = Field(None, description="Location of the event")
    attendees: List[str] = Field(default_factory=list, description="List of attendee email addresses")


class Tile(BaseModel):
    """Model for a tile representing a piece of content."""
    
    id: str = Field(..., description="Unique identifier for the tile")
    title: str = Field(..., description="Title of the tile")
    content: str = Field(..., description="Main content of the tile")
    source: str = Field(..., description="Source of the tile (e.g., 'gmail', 'google_calendar')")
    source_id: str = Field(..., description="Original ID from the source system")
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    updated_at: Optional[str] = Field(None, description="Last update timestamp")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata specific to the tile type"
    )
    related_events: List[RelatedEvent] = Field(
        default_factory=list,
        description="List of events related to this tile"
    )


class TileResponse(BaseModel):
    """Model for API responses containing tiles."""
    
    success: bool = Field(..., description="Whether the request was successful")
    count: int = Field(..., description="Number of tiles in the response")
    tiles: List[Tile] = Field(..., description="List of tiles")
    error: Optional[str] = Field(None, description="Error message if request failed") 