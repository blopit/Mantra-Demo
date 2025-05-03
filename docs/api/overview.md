# API Overview

This document provides an overview of the Mantra Demo API.

## Introduction

The Mantra Demo API is a RESTful API built with FastAPI. It provides endpoints for authentication, user management, and workflow management.

## Base URL

All API endpoints are relative to the base URL:

```
http://localhost:8000/api
```

## Authentication

Most API endpoints require authentication. The application uses session-based authentication with Google OAuth2.

To authenticate:

1. Call the `/api/google/auth` endpoint to get an authorization URL
2. Redirect the user to the authorization URL
3. Google will redirect back to the `/api/google/callback` endpoint
4. The application will create a session for the authenticated user

Once authenticated, the session cookie will be included in all subsequent requests.

## API Versioning

The API is versioned using URL prefixes. The current version is v1:

```
/api/v1/...
```

## Response Format

All API responses are in JSON format. The general structure is:

### Success Response Format

```json
{
  "success": true,
  "data": {
    // Response data specific to the endpoint
  },
  "message": "Optional success message"
}
```

### Error Response Format

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

## Error Handling

Errors are returned with appropriate HTTP status codes and a standardized JSON response format.

### Common Error Codes

- `validation_error`: Invalid request parameters
- `unauthorized`: Authentication required
- `forbidden`: Insufficient permissions
- `not_found`: Resource not found
- `database_error`: Database-related error
- `server_error`: Internal server error

### HTTP Status Codes

- `400 Bad Request`: Invalid request parameters
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `422 Unprocessable Entity`: Validation error
- `500 Internal Server Error`: Server error

## Rate Limiting

The API implements rate limiting to prevent abuse. The limits are:

- 100 requests per minute per IP address
- 1000 requests per hour per user

Rate limit headers are included in all responses:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 99
X-RateLimit-Reset: 1620000000
```

## API Documentation

Interactive API documentation is available at:

```
http://localhost:8000/docs
```

This provides a Swagger UI interface for exploring and testing the API.

## API Endpoints

The API is organized into the following groups:

### Authentication

- `GET /api/google/auth`: Initiate Google OAuth2 authentication
- `GET /api/google/callback`: Handle Google OAuth2 callback
- `GET /api/google/logout`: Log out the current user

### Users

- `GET /api/users/me`: Get the current user's profile
- `PUT /api/users/me`: Update the current user's profile

### Mantras (Workflows)

- `GET /api/mantras`: List all mantras
- `POST /api/mantras`: Create a new mantra
- `GET /api/mantras/{id}`: Get a specific mantra
- `PUT /api/mantras/{id}`: Update a mantra
- `DELETE /api/mantras/{id}`: Delete a mantra

### Installations

- `GET /api/installations`: List all installations for the current user
- `POST /api/installations`: Install a mantra
- `GET /api/installations/{id}`: Get a specific installation
- `PUT /api/installations/{id}`: Update an installation
- `DELETE /api/installations/{id}`: Uninstall a mantra

### Google Services

- `GET /api/google/gmail/messages`: List Gmail messages
- `GET /api/google/calendar/events`: List Calendar events

## Further Reading

- [API Routes](routes.md): Detailed documentation for each API endpoint
- [API Examples](examples.md): Example API requests and responses
