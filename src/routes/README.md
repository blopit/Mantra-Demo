# Mantra Demo Routes

This directory contains the route handlers for the Mantra Demo application.

## Overview

The routes are organized by functionality:

- `google_auth_consolidated.py`: Consolidated Google authentication routes
- `google_tiles.py`: Google tiles and visualization routes
- `mantra.py`: Mantra-specific routes
- `google_integration.py`: Google integration routes (auto-generated)
- `google_integration_wrapper.py`: Wrapper for Google integration routes with standardized responses

## Route Organization

All routes have been consolidated from the `custom_routes` directory into this directory to avoid duplication and improve maintainability.

## API Response Format

All routes use a standardized API response format:

### Success Response

```json
{
  "success": true,
  "data": {
    // Response data specific to the endpoint
  },
  "message": "Optional success message"
}
```

### Error Response

```json
{
  "success": false,
  "error": {
    "message": "Human-readable error message",
    "code": "error_code",
    "details": {
      // Optional additional error details
    }
  }
}
```

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

## Google Tiles

The `google_tiles.py` module provides routes for fetching and displaying tiles created from a user's Google/Gmail data.

### Endpoints

- `GET /api/google-tiles/view`: View tiles as HTML
- `GET /api/google-tiles/tiles`: Get tiles as JSON

## Usage

```python
# In app.py
from src.routes.google_auth_consolidated import router as google_auth_router
from src.routes.google_tiles import router as google_tiles_router
from src.routes.mantra import router as mantra_router
from src.routes.google_integration_wrapper import router as google_integration_router

app.include_router(google_auth_router)
app.include_router(google_tiles_router)
app.include_router(mantra_router)
app.include_router(google_integration_router)
```

## Error Handling

All routes use centralized error handling through the middleware defined in `src/middleware/error_handler.py`. This ensures consistent error responses across all endpoints.

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
