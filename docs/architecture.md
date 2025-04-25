# Architecture

This document describes the architecture of the Mantra Demo application.

## Overview

The Mantra Demo is a FastAPI-based application that showcases:

- Google OAuth2 authentication flow
- Secure credential storage in database
- Optional credential storage in DATABASE_URL environment variable
- Integration with Google services (Gmail, Calendar)
- SQLAlchemy ORM for database operations
- Clean architecture with separation of concerns

## Core Components

### Application Entry Point

- `app.py`: Main application entry point and FastAPI configuration
- `src/main.py`: Core application logic and initialization

### Database Models

- `src/models/`: SQLAlchemy database models
  - `base.py`: Base model configuration
  - `users.py`: User model
  - `google_integration.py`: Google integration model
  - `contacts.py`: Contacts model

### Utilities

- `src/utils/`: Utility functions
  - `database.py`: Database connection and session management
  - `google_credentials.py`: Google credentials management
  - `logger.py`: Logging configuration

### Routes and API Endpoints

- `src/routes/`: Route handlers
  - `google_auth_consolidated.py`: Consolidated Google authentication routes
  - `google_integration.py`: Google integration routes
  - `mantra.py`: Mantra-specific routes

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
- `src/static/`: Static assets
  - `css/`: CSS stylesheets
  - `js/`: JavaScript files

### Tests

- `tests/`: Test suite
  - `unit/`: Unit tests
  - `integration/`: Integration tests
  - `conftest.py`: Test fixtures and configuration

### Database Migrations

- `alembic/`: Database migration scripts
- `alembic.ini`: Alembic configuration

## Database Schema

### Users

- **Users**: Stores user information
  - id (UUID): Primary key
  - email (String): User's email address
  - name (String): User's name
  - is_active (Boolean): User's active status
  - created_at, updated_at: Timestamps

### Google Integration

- **GoogleIntegration**: Stores Google OAuth credentials
  - id (UUID): Primary key
  - user_id (UUID): Foreign key to Users
  - email (String): Google account email
  - access_token, refresh_token: OAuth tokens
  - scopes: Authorized scopes
  - token_expiry: Token expiration timestamp
  - status: Integration status (active, disconnected)
  - created_at, updated_at: Timestamps
