# Calendar Provider

This directory contains the Google Calendar provider implementation for Ultimate Assistant. The Calendar provider enables the application to interact with the Google Calendar API for reading, creating, and managing calendar events.

## Components

- `adapter.py` - Main adapter class for Calendar API integration
- `models.py` - Data models for calendar events and related entities
- `service.py` - Service class with higher-level Calendar operations

## Usage

```python
from src.providers.google.calendar import CalendarAdapter
from src.providers.google.auth import GoogleCredentialsManager

# Get credentials
credentials_manager = GoogleCredentialsManager()
credentials = credentials_manager.get_credentials(user_id)

# Initialize and connect to Calendar
calendar_adapter = CalendarAdapter()
await calendar_adapter.connect(credentials)

# Fetch upcoming events
events = await calendar_adapter.fetch_data(days_ahead=7)

# Create a new event
result = await calendar_adapter.push_data({
    'summary': 'Team Meeting',
    'start': '2023-05-10T10:00:00Z',
    'end': '2023-05-10T11:00:00Z',
    'description': 'Weekly team sync',
    'attendees': ['colleague@example.com']
})

# Disconnect when done
await calendar_adapter.disconnect()
```

## Data Models

The `models.py` file defines the following data models:

- `CalendarEvent` - Represents a calendar event with properties like summary, start/end times, attendees, etc.
- `CalendarAttendee` - Represents an attendee for a calendar event

## Testing

The Calendar provider can be tested using the test mode:

```python
import os
os.environ['TEST_MODE'] = 'true'

# In test mode, the adapter will return mock data instead of making real API calls
calendar_adapter = CalendarAdapter()
await calendar_adapter.connect({})  # Empty credentials are fine in test mode
events = await calendar_adapter.fetch_data()
```

## Error Handling

The adapter includes comprehensive error handling for common Calendar API issues:
- Authentication errors
- Rate limiting
- Network failures
- Invalid requests

Errors are logged using the standard Python logging module.

## Related Components

- `src/providers/google/auth/` - Authentication components for Google APIs
- `tests/integrations/test_calendar_adapter.py` - Tests for the Calendar adapter
