# Mantra-Demo

Demo example for Mantra Integration Manager with Google Sign-In

## Overview

This application demonstrates how to implement Google Sign-In and store the credentials in the DATABASE_URL environment variable. It provides a clean, organized approach to authentication with minimal duplication.

The Mantra Demo is a FastAPI-based application that showcases:

- Google OAuth2 authentication flow
- Secure credential storage in database
- Optional credential storage in DATABASE_URL environment variable
- Integration with Google services (Gmail, Calendar)
- SQLAlchemy ORM for database operations
- Clean architecture with separation of concerns

## Setup

1. Create a Google Cloud project and enable the Google OAuth API
2. Create OAuth credentials (Web application type)
3. Add authorized redirect URIs: `http://localhost:8000/api/google/callback`
4. Copy your Client ID and Client Secret
5. Create a `.env` file based on `.env.example` and add your Google credentials:

```
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
SESSION_SECRET_KEY=your-secret-key-here
```

## Installation

```bash
pip install -r requirements.txt
```

## Running the Application

```bash
python app.py
```

Then open your browser to http://localhost:8000

## How It Works

1. User clicks the "Sign in with Google" button
2. User can choose whether to store credentials in DATABASE_URL
3. User is redirected to Google's OAuth consent screen
4. After authentication, Google redirects back to the application
5. The application stores the credentials in the database and optionally in DATABASE_URL
6. The credentials can be accessed using the utility functions in `src/utils/google_credentials.py`

## Code Organization

The project follows a modular architecture with clear separation of concerns:

### Core Components

- `app.py`: Main application entry point and FastAPI configuration
- `src/models/`: SQLAlchemy database models
  - `base.py`: Base model configuration
  - `users.py`: User model
  - `google_integration.py`: Google integration model
  - `contacts.py`: Contacts model
- `src/utils/`: Utility functions
  - `database.py`: Database connection and session management
  - `google_credentials.py`: Google credentials management
  - `logger.py`: Logging configuration

### Routes and API Endpoints

- `src/custom_routes/`: Custom route handlers
  - `google/auth.py`: Google authentication routes
  - `google/tile_routes.py`: Google tile-related routes
- `src/routes/`: Standard route handlers
  - `google.py`: Google service routes
  - `google_auth.py`: Google authentication routes
  - `google_integration.py`: Google integration routes

### Service Providers

- `src/providers/`: Service provider implementations
  - `google/`: Google service providers
    - `auth/`: Authentication components
    - `calendar/`: Calendar service components
    - `gmail/`: Gmail service components
    - `common/`: Shared utilities

### Templates and Static Files

- `src/templates/`: HTML templates
  - `google_signin.html`: Google sign-in page

### Tests

- `tests/`: Test suite
  - `unit/`: Unit tests
  - `integration/`: Integration tests
  - `conftest.py`: Test fixtures and configuration

### Database Migrations

- `alembic/`: Database migration scripts
- `alembic.ini`: Alembic configuration

## Using the Credentials

To use the stored credentials in your code:

```python
from src.utils.google_credentials import get_credentials, get_credentials_object

# Get credentials as a dictionary
credentials_dict = get_credentials()

# Or get as a Google Credentials object
credentials = get_credentials_object()

# Use with Google API
from googleapiclient.discovery import build
service = build('gmail', 'v1', credentials=credentials)
```

### Using the Provider Classes

The application provides high-level provider classes for interacting with Google services:

```python
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

## Testing

The project includes comprehensive unit and integration tests. To run the tests:

### Install Testing Dependencies

```bash
pip install -r requirements.txt
```

### Run All Tests

```bash
./run_tests.py
```

### Run Specific Test Suites

```bash
# Run only unit tests
./run_tests.py --unit

# Run only integration tests
./run_tests.py --integration

# Run a specific test file
./run_tests.py tests/unit/test_google_credentials.py

# Run with verbose output
./run_tests.py -v

# Generate coverage report
./run_tests.py --coverage
```

The coverage report will be generated in the `htmlcov` directory. Open `htmlcov/index.html` in your browser to view the report.

## Architecture

### Authentication Flow

1. User initiates authentication via `/api/google/auth` endpoint
2. Application generates a state token and redirects to Google OAuth consent screen
3. User authenticates with Google and grants permissions
4. Google redirects back to `/api/google/callback` with authorization code
5. Application exchanges code for access and refresh tokens
6. Tokens are stored in the database and optionally in DATABASE_URL
7. User is now authenticated and can access Google services

### Database Schema

- **Users**: Stores user information
  - id (UUID): Primary key
  - email (String): User's email address
  - name (String): User's name
  - is_active (Boolean): User's active status
  - created_at, updated_at: Timestamps

- **GoogleIntegration**: Stores Google OAuth credentials
  - id (UUID): Primary key
  - user_id (UUID): Foreign key to Users
  - email (String): Google account email
  - access_token, refresh_token: OAuth tokens
  - scopes: Authorized scopes
  - token_expiry: Token expiration timestamp
  - status: Integration status (active, disconnected)
  - created_at, updated_at: Timestamps

## Known Issues and TODOs

- **Security**: Hardcoded user ID in `get_current_user` function should be replaced with proper authentication
- **Duplication**: Some duplication exists between `custom_routes` and `routes` directories
- **Error Handling**: Improve error handling and user feedback
- **Testing**: Increase test coverage, especially for edge cases
- **Documentation**: Add API documentation with Swagger/OpenAPI

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
