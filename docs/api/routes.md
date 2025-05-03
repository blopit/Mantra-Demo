# API Routes

This document provides detailed documentation for each API endpoint in the Mantra Demo application.

## Authentication

### Initiate Google OAuth2 Authentication

```
GET /api/google/auth
```

Initiates the Google OAuth2 authentication flow.

**Response**:

```json
{
  "auth_url": "https://accounts.google.com/o/oauth2/auth?..."
}
```

### Handle Google OAuth2 Callback

```
GET /api/google/callback
```

Handles the callback from Google OAuth2 authentication.

**Query Parameters**:

- `code` (required): The authorization code from Google
- `state` (optional): The state parameter from the authorization request

**Response**:

Redirects to the home page on successful authentication.

### Logout

```
GET /api/google/logout
```

Logs out the current user by clearing the session.

**Response**:

Redirects to the login page.

## Users

### Get Current User

```
GET /api/users/me
```

Returns the profile of the currently authenticated user.

**Response**:

```json
{
  "id": "user-id",
  "email": "user@example.com",
  "name": "User Name",
  "is_active": true,
  "created_at": "2023-01-01T00:00:00Z",
  "updated_at": "2023-01-01T00:00:00Z"
}
```

### Update Current User

```
PUT /api/users/me
```

Updates the profile of the currently authenticated user.

**Request Body**:

```json
{
  "name": "New Name"
}
```

**Response**:

```json
{
  "id": "user-id",
  "email": "user@example.com",
  "name": "New Name",
  "is_active": true,
  "created_at": "2023-01-01T00:00:00Z",
  "updated_at": "2023-01-01T00:00:00Z"
}
```

## Mantras (Workflows)

### List Mantras

```
GET /api/mantras
```

Returns a list of all mantras.

**Query Parameters**:

- `skip` (optional): Number of items to skip (default: 0)
- `limit` (optional): Maximum number of items to return (default: 100)
- `user_id` (optional): Filter by user ID
- `is_active` (optional): Filter by active status

**Response**:

```json
[
  {
    "id": "mantra-id-1",
    "name": "Mantra 1",
    "description": "Description of Mantra 1",
    "user_id": "user-id",
    "is_active": true,
    "created_at": "2023-01-01T00:00:00Z",
    "updated_at": "2023-01-01T00:00:00Z"
  },
  {
    "id": "mantra-id-2",
    "name": "Mantra 2",
    "description": "Description of Mantra 2",
    "user_id": "user-id",
    "is_active": true,
    "created_at": "2023-01-01T00:00:00Z",
    "updated_at": "2023-01-01T00:00:00Z"
  }
]
```

### Create Mantra

```
POST /api/mantras
```

Creates a new mantra.

**Request Body**:

```json
{
  "name": "New Mantra",
  "description": "Description of the new mantra",
  "workflow_json": {
    "nodes": [],
    "connections": {}
  },
  "is_active": true
}
```

**Response**:

```json
{
  "id": "new-mantra-id",
  "name": "New Mantra",
  "description": "Description of the new mantra",
  "user_id": "user-id",
  "is_active": true,
  "created_at": "2023-01-01T00:00:00Z",
  "updated_at": "2023-01-01T00:00:00Z"
}
```

### Get Mantra

```
GET /api/mantras/{id}
```

Returns a specific mantra.

**Path Parameters**:

- `id` (required): The ID of the mantra

**Response**:

```json
{
  "id": "mantra-id",
  "name": "Mantra Name",
  "description": "Description of the mantra",
  "workflow_json": {
    "nodes": [],
    "connections": {}
  },
  "user_id": "user-id",
  "is_active": true,
  "created_at": "2023-01-01T00:00:00Z",
  "updated_at": "2023-01-01T00:00:00Z"
}
```

### Update Mantra

```
PUT /api/mantras/{id}
```

Updates a specific mantra.

**Path Parameters**:

- `id` (required): The ID of the mantra

**Request Body**:

```json
{
  "name": "Updated Mantra Name",
  "description": "Updated description",
  "workflow_json": {
    "nodes": [],
    "connections": {}
  },
  "is_active": true
}
```

**Response**:

```json
{
  "id": "mantra-id",
  "name": "Updated Mantra Name",
  "description": "Updated description",
  "workflow_json": {
    "nodes": [],
    "connections": {}
  },
  "user_id": "user-id",
  "is_active": true,
  "created_at": "2023-01-01T00:00:00Z",
  "updated_at": "2023-01-01T00:00:00Z"
}
```

### Delete Mantra

```
DELETE /api/mantras/{id}
```

Deletes a specific mantra.

**Path Parameters**:

- `id` (required): The ID of the mantra

**Response**:

```json
{
  "message": "Mantra deleted successfully"
}
```

## Installations

### List Installations

```
GET /api/installations
```

Returns a list of all installations for the current user.

**Query Parameters**:

- `skip` (optional): Number of items to skip (default: 0)
- `limit` (optional): Maximum number of items to return (default: 100)
- `mantra_id` (optional): Filter by mantra ID
- `is_active` (optional): Filter by active status

**Response**:

```json
[
  {
    "id": "installation-id-1",
    "mantra_id": "mantra-id-1",
    "user_id": "user-id",
    "n8n_workflow_id": "n8n-workflow-id-1",
    "is_active": true,
    "created_at": "2023-01-01T00:00:00Z",
    "updated_at": "2023-01-01T00:00:00Z"
  },
  {
    "id": "installation-id-2",
    "mantra_id": "mantra-id-2",
    "user_id": "user-id",
    "n8n_workflow_id": "n8n-workflow-id-2",
    "is_active": true,
    "created_at": "2023-01-01T00:00:00Z",
    "updated_at": "2023-01-01T00:00:00Z"
  }
]
```

### Install Mantra

```
POST /api/installations
```

Installs a mantra for the current user.

**Request Body**:

```json
{
  "mantra_id": "mantra-id"
}
```

**Response**:

```json
{
  "id": "installation-id",
  "mantra_id": "mantra-id",
  "user_id": "user-id",
  "n8n_workflow_id": "n8n-workflow-id",
  "is_active": true,
  "created_at": "2023-01-01T00:00:00Z",
  "updated_at": "2023-01-01T00:00:00Z"
}
```

### Get Installation

```
GET /api/installations/{id}
```

Returns a specific installation.

**Path Parameters**:

- `id` (required): The ID of the installation

**Response**:

```json
{
  "id": "installation-id",
  "mantra_id": "mantra-id",
  "user_id": "user-id",
  "n8n_workflow_id": "n8n-workflow-id",
  "is_active": true,
  "created_at": "2023-01-01T00:00:00Z",
  "updated_at": "2023-01-01T00:00:00Z"
}
```

### Update Installation

```
PUT /api/installations/{id}
```

Updates a specific installation.

**Path Parameters**:

- `id` (required): The ID of the installation

**Request Body**:

```json
{
  "is_active": false
}
```

**Response**:

```json
{
  "id": "installation-id",
  "mantra_id": "mantra-id",
  "user_id": "user-id",
  "n8n_workflow_id": "n8n-workflow-id",
  "is_active": false,
  "created_at": "2023-01-01T00:00:00Z",
  "updated_at": "2023-01-01T00:00:00Z"
}
```

### Uninstall Mantra

```
DELETE /api/installations/{id}
```

Uninstalls a mantra for the current user.

**Path Parameters**:

- `id` (required): The ID of the installation

**Response**:

```json
{
  "message": "Installation deleted successfully"
}
```

## Google Services

### List Gmail Messages

```
GET /api/google/gmail/messages
```

Returns a list of Gmail messages for the current user.

**Query Parameters**:

- `max_results` (optional): Maximum number of messages to return (default: 10)
- `query` (optional): Gmail search query

**Response**:

```json
[
  {
    "id": "message-id-1",
    "thread_id": "thread-id-1",
    "snippet": "Message snippet...",
    "subject": "Message subject",
    "from": "sender@example.com",
    "date": "2023-01-01T00:00:00Z"
  },
  {
    "id": "message-id-2",
    "thread_id": "thread-id-2",
    "snippet": "Message snippet...",
    "subject": "Message subject",
    "from": "sender@example.com",
    "date": "2023-01-01T00:00:00Z"
  }
]
```

### List Calendar Events

```
GET /api/google/calendar/events
```

Returns a list of Calendar events for the current user.

**Query Parameters**:

- `max_results` (optional): Maximum number of events to return (default: 10)
- `time_min` (optional): Start time (default: now)
- `time_max` (optional): End time (default: 7 days from now)

**Response**:

```json
[
  {
    "id": "event-id-1",
    "summary": "Event summary",
    "description": "Event description",
    "start": {
      "dateTime": "2023-01-01T10:00:00Z"
    },
    "end": {
      "dateTime": "2023-01-01T11:00:00Z"
    },
    "location": "Event location"
  },
  {
    "id": "event-id-2",
    "summary": "Event summary",
    "description": "Event description",
    "start": {
      "dateTime": "2023-01-02T10:00:00Z"
    },
    "end": {
      "dateTime": "2023-01-02T11:00:00Z"
    },
    "location": "Event location"
  }
]
```

## Further Reading

- [API Overview](overview.md): General information about the API
- [API Examples](examples.md): Example API requests and responses
