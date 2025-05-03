# Authentication Flow

This document describes the authentication flow in the Mantra Demo application.

## Overview

The application uses Google OAuth2 for authentication. This provides a secure, standards-based way to authenticate users and access Google APIs on their behalf.

## Authentication Flow Diagram

```
┌─────────┐                  ┌─────────────┐                  ┌─────────┐
│         │                  │             │                  │         │
│  User   │                  │ Mantra App  │                  │ Google  │
│         │                  │             │                  │         │
└────┬────┘                  └──────┬──────┘                  └────┬────┘
     │                              │                               │
     │    1. Click Sign In          │                               │
     │ ─────────────────────────────>                               │
     │                              │                               │
     │                              │    2. Redirect to Google      │
     │                              │ ─────────────────────────────>│
     │                              │                               │
     │                              │                               │
     │    3. Google Login Page      │                               │
     │ <─────────────────────────────────────────────────────────────
     │                              │                               │
     │    4. Enter Credentials      │                               │
     │ ─────────────────────────────────────────────────────────────>
     │                              │                               │
     │                              │                               │
     │                              │    5. Authorization Code      │
     │                              │ <─────────────────────────────│
     │                              │                               │
     │                              │    6. Exchange for Tokens     │
     │                              │ ─────────────────────────────>│
     │                              │                               │
     │                              │    7. Access & Refresh Tokens │
     │                              │ <─────────────────────────────│
     │                              │                               │
     │    8. Redirect to App        │                               │
     │ <─────────────────────────────                               │
     │                              │                               │
     │    9. User is Authenticated  │                               │
     │ <─────────────────────────────                               │
     │                              │                               │
```

## Step-by-Step Process

### 1. Initiate Authentication

The user clicks the "Sign in with Google" button, which triggers a request to the `/api/google/auth` endpoint.

```python
@router.get("/auth")
async def google_auth():
    """
    Initiate Google OAuth2 authentication flow.
    
    Returns:
        dict: A dictionary containing the authorization URL
    """
    auth_url = get_authorization_url()
    return {"auth_url": auth_url}
```

### 2. Redirect to Google

The application generates an OAuth2 authorization URL and redirects the user to Google's authentication page.

```python
def get_authorization_url():
    """
    Generate Google OAuth2 authorization URL.
    
    Returns:
        str: The authorization URL
    """
    flow = Flow.from_client_config(
        client_config=get_client_config(),
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )
    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent"
    )
    return authorization_url
```

### 3. User Authentication

The user enters their Google credentials and grants the requested permissions.

### 4. Authorization Code

Google redirects back to the application's callback URL with an authorization code.

### 5. Exchange for Tokens

The application exchanges the authorization code for access and refresh tokens.

```python
@router.get("/callback")
async def google_callback(
    request: Request,
    code: str = Query(...),
    state: str = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Handle Google OAuth2 callback.
    
    Args:
        request: The request object
        code: The authorization code from Google
        state: The state parameter from the authorization request
        db: The database session
        
    Returns:
        RedirectResponse: Redirect to the home page
    """
    # Exchange authorization code for tokens
    flow = Flow.from_client_config(
        client_config=get_client_config(),
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )
    flow.fetch_token(code=code)
    credentials = flow.credentials
    
    # Get user info from Google
    user_info = get_user_info(credentials)
    
    # Create or update user
    user = await get_or_create_user(db, user_info)
    
    # Store credentials
    await store_credentials(db, user.id, credentials)
    
    # Set session
    request.session["user"] = {
        "id": user.id,
        "email": user.email,
        "name": user.name
    }
    
    return RedirectResponse(url="/")
```

### 6. Store Credentials

The application stores the tokens securely in the database.

```python
async def store_credentials(db: AsyncSession, user_id: str, credentials: Credentials):
    """
    Store Google OAuth credentials in the database.
    
    Args:
        db: The database session
        user_id: The user ID
        credentials: The Google OAuth credentials
    """
    # Convert credentials to JSON
    credentials_dict = {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": credentials.scopes
    }
    
    # Check if credentials already exist
    result = await db.execute(
        select(GoogleAuth).where(GoogleAuth.user_id == user_id)
    )
    google_auth = result.scalars().first()
    
    if google_auth:
        # Update existing credentials
        google_auth.credentials = credentials_dict
    else:
        # Create new credentials
        google_auth = GoogleAuth(
            user_id=user_id,
            credentials=credentials_dict
        )
        db.add(google_auth)
    
    await db.commit()
```

### 7. Session Management

The application creates a session for the authenticated user.

```python
# Set session
request.session["user"] = {
    "id": user.id,
    "email": user.email,
    "name": user.name
}
```

## Token Refresh

When access tokens expire, the application uses the refresh token to obtain new tokens.

```python
async def refresh_credentials(db: AsyncSession, user_id: str):
    """
    Refresh Google OAuth credentials.
    
    Args:
        db: The database session
        user_id: The user ID
        
    Returns:
        Credentials: The refreshed credentials
    """
    # Get credentials from database
    result = await db.execute(
        select(GoogleAuth).where(GoogleAuth.user_id == user_id)
    )
    google_auth = result.scalars().first()
    
    if not google_auth:
        raise CredentialsNotFoundError(f"No credentials found for user {user_id}")
    
    # Create credentials object
    credentials = Credentials(
        token=google_auth.credentials["token"],
        refresh_token=google_auth.credentials["refresh_token"],
        token_uri=google_auth.credentials["token_uri"],
        client_id=google_auth.credentials["client_id"],
        client_secret=google_auth.credentials["client_secret"],
        scopes=google_auth.credentials["scopes"]
    )
    
    # Refresh if expired
    if credentials.expired:
        request = google.auth.transport.requests.Request()
        credentials.refresh(request)
        
        # Update credentials in database
        google_auth.credentials = {
            "token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": credentials.token_uri,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "scopes": credentials.scopes
        }
        await db.commit()
    
    return credentials
```

## Security Considerations

1. **HTTPS**: All communication should be over HTTPS to prevent token interception.
2. **State Parameter**: The state parameter is used to prevent CSRF attacks.
3. **Secure Storage**: Tokens are stored securely in the database.
4. **Minimal Scopes**: Only request the minimum scopes needed for the application.
5. **Token Refresh**: Refresh tokens when they expire rather than requiring re-authentication.

## Further Reading

- [Google OAuth2 Documentation](https://developers.google.com/identity/protocols/oauth2)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [Google Providers](../guides/google_integration.md): How to use Google services in the application
