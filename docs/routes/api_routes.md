# API Routes

This document describes the API routes implemented in the Mantra Demo application.

## Google Authentication Routes

The Google authentication routes are implemented in `src/routes/google_auth_consolidated.py`.

### Endpoints

- `GET /api/google/auth`: Get Google OAuth URL
- `GET /api/google/callback`: Handle Google OAuth callback
- `GET /api/google/status`: Get Google integration status
- `POST /api/google/disconnect`: Disconnect Google account
- `GET /api/google/refresh`: Refresh Google OAuth token

### Authentication Flow

1. User initiates authentication via `/api/google/auth` endpoint
2. Application generates a state token and redirects to Google OAuth consent screen
3. User authenticates with Google and grants permissions
4. Google redirects back to `/api/google/callback` with authorization code
5. Application exchanges code for access and refresh tokens
6. Tokens are stored in the database and optionally in DATABASE_URL
7. User is now authenticated and can access Google services

## Google Integration Routes

The Google integration routes are implemented in `src/routes/google_integration.py`.

### Endpoints

- `GET /api/google/integration/status`: Get integration status
- `POST /api/google/integration/connect`: Connect Google account
- `POST /api/google/integration/disconnect`: Disconnect Google account

## Mantra Routes

The Mantra-specific routes are implemented in `src/routes/mantra.py`.

### Endpoints

- `GET /api/mantra`: Get all mantras
- `POST /api/mantra`: Create a new mantra
- `GET /api/mantra/{mantra_id}`: Get a specific mantra
- `PUT /api/mantra/{mantra_id}`: Update a mantra
- `DELETE /api/mantra/{mantra_id}`: Delete a mantra

## Best Practices

- Keep route handlers focused on request/response handling
- Move business logic to service modules
- Use dependency injection for database sessions
- Document all endpoints with docstrings
- Use Pydantic models for request/response validation
