# Google Service Providers

This document describes the Google service providers implemented in the Mantra Demo application.

## Structure

The Google providers are organized in a modular structure:

```
providers/
├── google/
│   ├── __init__.py
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── manager.py
│   │   └── credentials.py
│   ├── gmail/
│   │   ├── __init__.py
│   │   ├── adapter.py
│   │   └── service.py
│   ├── calendar/
│   │   ├── __init__.py
│   │   ├── adapter.py
│   │   └── service.py
│   ├── common/
│   │   └── __init__.py
│   └── helpers.py
```

## Authentication

The `auth` module provides authentication functionality for Google services:

- `manager.py`: Handles OAuth flow and token management
- `credentials.py`: Manages credential storage and retrieval

## Gmail Service

The `gmail` module provides Gmail API integration:

- `adapter.py`: Low-level adapter for Gmail API
- `service.py`: High-level service for Gmail operations

## Calendar Service

The `calendar` module provides Calendar API integration:

- `adapter.py`: Low-level adapter for Calendar API
- `service.py`: High-level service for Calendar operations

## Usage Examples

```python
# Import Google services
from src.providers.google import GoogleAuthManager, GmailService, GoogleCredentialsManager

# Initialize services
auth_manager = GoogleAuthManager()
gmail_service = GmailService()
credentials_manager = GoogleCredentialsManager()

# Using Gmail service
from src.providers.google.gmail import GmailService
from sqlalchemy.orm import Session

def get_emails(user_id: str, db: Session):
    gmail_service = GmailService(user_id, db)
    messages = gmail_service.list_messages(max_results=10)
    return messages

# Using Calendar service
from src.providers.google.calendar import CalendarService

def get_events(user_id: str, db: Session):
    calendar_service = CalendarService(user_id, db)
    events = calendar_service.list_events()
    return events
```
