# Mantra Demo Routes

This directory contains the route handlers for the Mantra Demo application.

## Overview

The routes are organized by functionality:

- `google_auth_consolidated.py`: Consolidated Google authentication routes
- `mantra.py`: Mantra-specific routes
- `google_integration.py`: Google integration routes

## Google Authentication

The `google_auth_consolidated.py` module provides a unified interface for Google OAuth authentication. It combines functionality that was previously spread across multiple files:

- `src/routes/google.py`
- `src/routes/google_auth.py`
- `src/custom_routes/google/auth.py`

### Features

- OAuth 2.0 authentication flow with Google
- Token management (refresh, revocation)
- User profile information retrieval
- Session-based authentication
- Database storage of credentials

### Endpoints

- `GET /api/google/auth`: Get Google OAuth URL
- `GET /api/google/callback`: Handle Google OAuth callback
- `GET /api/google/status`: Get Google integration status
- `POST /api/google/disconnect`: Disconnect Google account
- `GET /api/google/refresh`: Refresh Google OAuth token

### Usage

```python
# In app.py or main.py
from src.routes.google_auth_consolidated import router as google_auth_router
app.include_router(google_auth_router)
```

## Best Practices

- Keep route handlers focused on request/response handling
- Move business logic to service modules
- Use dependency injection for database sessions
- Document all endpoints with docstrings
- Use Pydantic models for request/response validation

## Technical Debt

- The `google_auth.py` and `google.py` files are kept for backward compatibility but should be removed in a future release
- Some routes in `mantra.py` could be further optimized
- Consider adding more comprehensive error handling
