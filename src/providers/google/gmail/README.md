# Gmail Provider

This directory contains the Gmail provider implementation for Ultimate Assistant. The Gmail provider enables the application to interact with the Gmail API for reading, sending, and managing emails.

## Components

- `adapter.py` - Main adapter class for Gmail API integration
- `models.py` - Data models for Gmail messages and attachments
- `service.py` - Service class with higher-level Gmail operations

## Usage

```python
from src.providers.google.gmail import GmailAdapter
from src.providers.google.auth import GoogleCredentialsManager

# Get credentials
credentials_manager = GoogleCredentialsManager()
credentials = credentials_manager.get_credentials(user_id)

# Initialize and connect to Gmail
gmail_adapter = GmailAdapter()
await gmail_adapter.connect(credentials)

# Fetch recent emails
emails = await gmail_adapter.fetch_data(limit=10)

# Send an email
result = await gmail_adapter.push_data({
    'to': 'recipient@example.com',
    'subject': 'Hello',
    'body': 'This is a test email'
})

# Disconnect when done
await gmail_adapter.disconnect()
```

## Data Models

The `models.py` file defines the following data models:

- `GmailMessage` - Represents an email message with properties like subject, sender, body, etc.
- `GmailAttachment` - Represents an email attachment with properties like filename, mime type, etc.

## Testing

The Gmail provider can be tested using the test mode:

```python
import os
os.environ['TEST_MODE'] = 'true'

# In test mode, the adapter will return mock data instead of making real API calls
gmail_adapter = GmailAdapter()
await gmail_adapter.connect({})  # Empty credentials are fine in test mode
emails = await gmail_adapter.fetch_data()
```

## Error Handling

The adapter includes comprehensive error handling for common Gmail API issues:
- Authentication errors
- Rate limiting
- Network failures
- Invalid requests

Errors are logged using the standard Python logging module.

## Related Components

- `src/providers/google/auth/` - Authentication components for Google APIs
- `src/agents/tools/gmail_tool.py` - Agent tool that uses this provider
- `tests/integrations/test_gmail_adapter.py` - Tests for the Gmail adapter
