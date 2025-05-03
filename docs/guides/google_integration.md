# Google Integration Guide

This guide explains how to integrate with Google services in the Mantra Demo application.

## Overview

The application integrates with Google services using the Google API Client Library for Python. It supports the following Google services:

- **Gmail**: Access to email messages
- **Calendar**: Access to calendar events
- **People**: Access to contacts

## Authentication

The application uses OAuth2 for authentication with Google services. The authentication flow is as follows:

1. User initiates the authentication flow by clicking "Sign in with Google"
2. User is redirected to Google's authentication page
3. User grants the requested permissions
4. Google redirects back to the application with an authorization code
5. The application exchanges the code for access and refresh tokens
6. The tokens are stored securely in the database
7. The application uses the tokens to access Google services on behalf of the user

## Required Scopes

The application requests the following OAuth scopes:

- `https://www.googleapis.com/auth/userinfo.email`: Access to user's email address
- `https://www.googleapis.com/auth/userinfo.profile`: Access to user's profile information
- `https://www.googleapis.com/auth/gmail.readonly`: Read-only access to Gmail
- `https://www.googleapis.com/auth/calendar.readonly`: Read-only access to Calendar

## Setting Up Google OAuth

### Step 1: Create a Google Cloud Project

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the required APIs:
   - Google OAuth2 API
   - Gmail API
   - Calendar API
   - People API

### Step 2: Configure OAuth Consent Screen

1. Go to "APIs & Services" > "OAuth consent screen"
2. Select "External" user type (or "Internal" if you're using Google Workspace)
3. Fill in the required information:
   - App name
   - User support email
   - Developer contact information
4. Add the required scopes
5. Add test users if using External user type

### Step 3: Create OAuth Client ID

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth client ID"
3. Select "Web application" as the application type
4. Add authorized JavaScript origins:
   - `http://localhost:8000` (for development)
   - Your production domain (for production)
5. Add authorized redirect URIs:
   - `http://localhost:8000/api/google/callback` (for development)
   - Your production callback URL (for production)
6. Click "Create"
7. Copy the Client ID and Client Secret

### Step 4: Configure Environment Variables

Add the following to your `.env` file:

```
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/api/google/callback
GOOGLE_AUTH_SCOPES=https://www.googleapis.com/auth/userinfo.email,https://www.googleapis.com/auth/userinfo.profile,https://www.googleapis.com/auth/gmail.readonly,https://www.googleapis.com/auth/calendar.readonly
```

## Using Google Services

### Getting Credentials

The application provides utility functions to get Google credentials:

```python
from src.utils.google_credentials import get_credentials, get_credentials_object

# Get credentials as a dictionary
credentials_dict = get_credentials(user_id)

# Get credentials as a Google Credentials object
credentials = get_credentials_object(user_id)
```

### Gmail Integration

```python
from googleapiclient.discovery import build
from src.utils.google_credentials import get_credentials_object

def get_gmail_messages(user_id, max_results=10, query=None):
    """Get Gmail messages for a user."""
    credentials = get_credentials_object(user_id)
    service = build('gmail', 'v1', credentials=credentials)
    
    # Get messages
    result = service.users().messages().list(
        userId='me',
        maxResults=max_results,
        q=query
    ).execute()
    
    messages = result.get('messages', [])
    
    # Get message details
    detailed_messages = []
    for message in messages:
        msg = service.users().messages().get(
            userId='me',
            id=message['id'],
            format='metadata',
            metadataHeaders=['Subject', 'From', 'Date']
        ).execute()
        
        # Extract headers
        headers = {h['name']: h['value'] for h in msg.get('payload', {}).get('headers', [])}
        
        detailed_messages.append({
            'id': msg['id'],
            'thread_id': msg['threadId'],
            'snippet': msg.get('snippet', ''),
            'subject': headers.get('Subject', ''),
            'from': headers.get('From', ''),
            'date': headers.get('Date', '')
        })
    
    return detailed_messages
```

### Calendar Integration

```python
from googleapiclient.discovery import build
from src.utils.google_credentials import get_credentials_object
from datetime import datetime, timedelta

def get_calendar_events(user_id, max_results=10, time_min=None, time_max=None):
    """Get Calendar events for a user."""
    credentials = get_credentials_object(user_id)
    service = build('calendar', 'v3', credentials=credentials)
    
    # Set default time range if not provided
    if time_min is None:
        time_min = datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
    if time_max is None:
        time_max = (datetime.utcnow() + timedelta(days=7)).isoformat() + 'Z'
    
    # Get events
    events_result = service.events().list(
        calendarId='primary',
        timeMin=time_min,
        timeMax=time_max,
        maxResults=max_results,
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    
    events = events_result.get('items', [])
    
    return events
```

### People Integration

```python
from googleapiclient.discovery import build
from src.utils.google_credentials import get_credentials_object

def get_contacts(user_id, max_results=10):
    """Get contacts for a user."""
    credentials = get_credentials_object(user_id)
    service = build('people', 'v1', credentials=credentials)
    
    # Get contacts
    results = service.people().connections().list(
        resourceName='people/me',
        pageSize=max_results,
        personFields='names,emailAddresses,phoneNumbers'
    ).execute()
    
    connections = results.get('connections', [])
    
    contacts = []
    for person in connections:
        names = person.get('names', [])
        email_addresses = person.get('emailAddresses', [])
        phone_numbers = person.get('phoneNumbers', [])
        
        contacts.append({
            'resource_name': person['resourceName'],
            'name': names[0].get('displayName', '') if names else '',
            'email': email_addresses[0].get('value', '') if email_addresses else '',
            'phone': phone_numbers[0].get('value', '') if phone_numbers else ''
        })
    
    return contacts
```

## Error Handling

When working with Google APIs, it's important to handle errors properly:

```python
from googleapiclient.errors import HttpError

try:
    # Call Google API
    result = service.users().messages().list(userId='me').execute()
except HttpError as error:
    if error.resp.status == 401:
        # Handle authentication errors
        # Refresh tokens or prompt for re-authentication
        pass
    elif error.resp.status == 403:
        # Handle permission errors
        # Request additional scopes
        pass
    elif error.resp.status == 404:
        # Handle not found errors
        pass
    else:
        # Handle other errors
        pass
```

## Token Refresh

The application automatically refreshes expired tokens:

```python
from src.utils.google_credentials import refresh_credentials

# Refresh credentials if expired
credentials = refresh_credentials(user_id)
```

## Best Practices

1. **Minimize API Calls**: Google APIs have rate limits, so minimize the number of calls
2. **Use Batch Requests**: When making multiple requests, use batch requests
3. **Handle Errors Gracefully**: Implement proper error handling
4. **Respect User Privacy**: Only request the minimum scopes needed
5. **Cache Results**: Cache API responses when appropriate

## Further Reading

- [Google API Client Library for Python](https://github.com/googleapis/google-api-python-client)
- [Google OAuth2 Documentation](https://developers.google.com/identity/protocols/oauth2)
- [Gmail API Documentation](https://developers.google.com/gmail/api)
- [Calendar API Documentation](https://developers.google.com/calendar)
- [People API Documentation](https://developers.google.com/people)
