# Google Authentication

This directory contains components for Google OAuth authentication in Ultimate Assistant. These components handle the OAuth flow, token management, and credential storage for Google API integrations.

## Components

- `manager.py` - Authentication manager for handling the OAuth flow
- `credentials.py` - Credentials manager for storing and retrieving tokens

## Authentication Flow

The Google authentication flow consists of these steps:

1. Generate an authorization URL with the required scopes
2. Redirect the user to the Google consent screen
3. Receive the authorization code from the callback
4. Exchange the code for access and refresh tokens
5. Store the tokens securely
6. Use the tokens to authenticate API requests
7. Refresh tokens when they expire

## Usage

```python
from src.providers.google.auth import GoogleAuthManager, GoogleCredentialsManager

# Initialize the auth manager
auth_manager = GoogleAuthManager()

# Generate an authorization URL
auth_url = auth_manager.get_authorization_url(
    redirect_uri="https://your-app.com/callback",
    scopes=["https://www.googleapis.com/auth/gmail.readonly"],
    state="user123"
)

# Exchange the code for credentials
credentials = auth_manager.exchange_code(
    code="authorization_code",
    redirect_uri="https://your-app.com/callback"
)

# Store the credentials
credentials_manager = GoogleCredentialsManager()
credentials_manager.store_credentials(user_id, credentials)

# Retrieve credentials later
stored_credentials = credentials_manager.get_credentials(user_id)

# Clear credentials when no longer needed
auth_manager.clear_credentials(stored_credentials)
```

## Token Refresh

The credentials manager automatically handles token refresh when tokens expire:

```python
# Get credentials (will be refreshed if expired)
credentials = credentials_manager.get_credentials(user_id)

# Use credentials with a Google service
gmail_service = build('gmail', 'v1', credentials=credentials)
```

## Security Considerations

- Tokens are stored in the database with encryption
- Refresh tokens are treated as sensitive data
- The application requests only the necessary scopes
- Tokens can be revoked when no longer needed

## Related Components

- `src/models/google_integration.py` - Database model for storing credentials
- `src/custom_routes/google/auth_routes.py` - API routes for the OAuth flow
- `tests/integrations/test_google_auth.py` - Tests for the authentication components
