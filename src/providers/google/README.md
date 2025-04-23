# Google Provider for Ultimate Assistant

This module provides integration with Google services for Ultimate Assistant.

## Features

- Authentication with Google OAuth2
- Gmail integration
- Google Calendar integration
- Common utilities for Google API interactions

## Installation

```bash
pip install ultimate-assistant-google-provider
```

## Usage

### Authentication

```python
from ultimate_assistant.providers.google.auth import GoogleAuthManager

# Initialize auth manager
auth_manager = GoogleAuthManager()

# Get authorization URL
auth_url = auth_manager.get_authorization_url(
    redirect_uri="https://your-app.com/callback",
    state="user123"
)

# Exchange code for credentials
credentials = auth_manager.exchange_code(
    code="authorization_code",
    redirect_uri="https://your-app.com/callback"
)
```

### Gmail

```python
from ultimate_assistant.providers.google.gmail import GmailService

# Initialize Gmail service
gmail_service = GmailService()

# Connect to Gmail
await gmail_service.connect(credentials)

# Get messages
messages = await gmail_service.get_messages(max_results=10)

# Send a message
await gmail_service.send_message(
    to="recipient@example.com",
    subject="Hello",
    body="This is a test email"
)
```

### Calendar

```python
from ultimate_assistant.providers.google.calendar import CalendarService

# Initialize Calendar service
calendar_service = CalendarService()

# Connect to Calendar
await calendar_service.connect(credentials)

# Get upcoming events
events = await calendar_service.get_events(days_ahead=7)

# Create an event
await calendar_service.create_event(
    summary="Team Meeting",
    start_time="2023-01-01T10:00:00Z",
    end_time="2023-01-01T11:00:00Z",
    description="Weekly team sync",
    location="Conference Room A",
    attendees=[{"email": "colleague@example.com"}]
)
```

## License

MIT
