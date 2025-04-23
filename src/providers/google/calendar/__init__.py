"""
Google Calendar module.

This module provides integration with Google Calendar API.
"""

from .adapter import CalendarAdapter
from .service import CalendarService

__all__ = ['CalendarAdapter', 'CalendarService']
