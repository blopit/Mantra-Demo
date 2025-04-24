# Mantra Demo Documentation

## Overview

Mantra Demo is a FastAPI-based application that demonstrates Google OAuth integration with credential storage in both database and environment variables. It provides a clean, organized approach to authentication with minimal duplication.

## Architecture

### Components

The application follows a modular architecture with clear separation of concerns:

1. **Core Application** (`app.py`): Main entry point that configures FastAPI, middleware, and routes
2. **Models** (`src/models/`): SQLAlchemy ORM models for database entities
3. **Routes** (`src/routes/` and `src/custom_routes/`): API endpoints and route handlers
4. **Providers** (`src/providers/`): Service providers for external integrations (Google)
5. **Utils** (`src/utils/`): Utility functions for database, logging, etc.
6. **Templates** (`src/templates/`): HTML templates for the web interface

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

## API Documentation

### Google Authentication Endpoints

#### `GET /api/google/auth`

Initiates the Google OAuth flow.

**Response:**
```json
{
  "auth_url": "https://accounts.google.com/o/oauth2/auth?..."
}
```

#### `GET /api/google/callback`

Handles the OAuth callback from Google.

**Query Parameters:**
- `code`: Authorization code from Google
- `state`: State parameter for CSRF protection

**Response:**
- Redirects to home page on success
- Returns error details on failure

#### `GET /api/google/status`

Gets the current Google connection status.

**Response:**
```json
{
  "is_connected": true,
  "email": "user@example.com",
  "scopes": ["https://www.googleapis.com/auth/gmail.readonly", "..."]
}
```

#### `GET /api/google/disconnect`

Disconnects the Google account.

**Response:**
```json
{
  "success": true,
  "message": "Google account disconnected"
}
```

### Google Integration Endpoints

#### `GET /api/google-integrations/`

Lists all Google integrations.

**Query Parameters:**
- `skip`: Number of records to skip (pagination)
- `limit`: Maximum number of records to return

**Response:**
```json
[
  {
    "id": "uuid",
    "user_id": "uuid",
    "email": "user@example.com",
    "status": "active",
    "created_at": "2023-01-01T00:00:00Z",
    "updated_at": "2023-01-01T00:00:00Z"
  }
]
```

#### `GET /api/google-integrations/{integration_id}`

Gets a specific Google integration.

**Path Parameters:**
- `integration_id`: UUID of the integration

**Response:**
```json
{
  "id": "uuid",
  "user_id": "uuid",
  "email": "user@example.com",
  "status": "active",
  "created_at": "2023-01-01T00:00:00Z",
  "updated_at": "2023-01-01T00:00:00Z"
}
```

## Code Documentation

### Models

#### Base Model

The `Base` class in `src/models/base.py` provides the foundation for all SQLAlchemy models.

#### Users Model

The `Users` class in `src/models/users.py` represents users in the system.

```python
class Users(Base):
    __tablename__ = "users"

    id = Column(UUIDType, primary_key=True, default=uuid4)
    email = Column(String, unique=True, nullable=False)
    name = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    google_integration = relationship("GoogleIntegration", back_populates="user", uselist=False)
    contacts = relationship("Contacts", back_populates="user")
```

#### GoogleIntegration Model

The `GoogleIntegration` class in `src/models/google_integration.py` stores OAuth credentials.

```python
class GoogleIntegration(Base):
    __tablename__ = "google_integrations"
    
    id = Column(UUIDType, primary_key=True, default=uuid4)
    user_id = Column(UUIDType, ForeignKey("users.id"), nullable=False)
    email = Column(String, nullable=False)
    access_token = Column(Text, nullable=True)
    refresh_token = Column(Text, nullable=True)
    scopes = Column(Text, nullable=True)
    token_expiry = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(20), nullable=False, default="active")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationship
    user = relationship("Users", back_populates="google_integration")
```

### Utilities

#### Database Utility

The `database.py` module provides database connection and session management.

```python
# Create database engine
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)

# Create all tables
Base.metadata.create_all(bind=engine)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """Dependency to get database session for FastAPI endpoints."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

#### Logger Utility

The `logger.py` module provides consistent logging across the application.

```python
def get_logger(name: Optional[str] = None, level: int = logging.INFO) -> logging.Logger:
    """Get a configured logger instance with consistent formatting."""
    logger = logging.getLogger(name or __name__)
    
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(level)
    
    return logger
```

### Google Authentication

The `GoogleAuthManager` class in `src/providers/google/auth/manager.py` handles OAuth flow.

```python
class GoogleAuthManager:
    """Manages Google authentication flow and credential lifecycle."""
    
    def get_authorization_url(self, redirect_uri: str, state: Optional[str] = None) -> str:
        """Get the URL for Google OAuth authorization."""
        # Implementation...
    
    def exchange_code(self, code: str, redirect_uri: str) -> Optional[Dict[str, Any]]:
        """Exchange an authorization code for credentials."""
        # Implementation...
    
    def validate_and_refresh(self, credentials_dict: Dict[str, Any]) -> bool:
        """Validate credentials and refresh them if needed."""
        # Implementation...
    
    async def get_credentials(self, user_id: uuid.UUID) -> Optional[Dict]:
        """Get stored Google OAuth credentials for a user."""
        # Implementation...
    
    async def save_credentials(self, user_id: uuid.UUID, credentials: Dict) -> bool:
        """Save or update Google OAuth credentials for a user."""
        # Implementation...
    
    async def clear_credentials(self, user_id: uuid.UUID) -> bool:
        """Clear Google OAuth credentials for a user."""
        # Implementation...
```

## Known Issues and TODOs

### Security Issues

1. **Hardcoded User ID**: In `src/custom_routes/google/auth.py`, there's a hardcoded user ID in the `get_current_user` function that should be replaced with proper authentication.

```python
# If user_id is not found, use hardcoded ID for now
# TODO: Implement proper authentication
user_id = "52cb4d8f-ca71-484b-9228-112070c4947a"
```

2. **Token Storage**: OAuth tokens are stored in plain text in the database. In a production environment, these should be encrypted.

3. **Session Security**: The session middleware uses a default secret key in development. This should be properly secured in production.

### Code Duplication

1. **Route Duplication**: There's duplication between `src/custom_routes` and `src/routes` directories. These should be consolidated.

2. **Authentication Logic**: Authentication logic is spread across multiple files. This should be centralized.

### Error Handling

1. **Inconsistent Error Handling**: Error handling is inconsistent across the application. A standardized approach should be implemented.

2. **Missing Validation**: Input validation is missing in some endpoints.

### Testing

1. **Test Coverage**: Test coverage should be increased, especially for edge cases.

2. **Integration Tests**: More comprehensive integration tests are needed.

### Documentation

1. **API Documentation**: Add Swagger/OpenAPI documentation for all endpoints.

2. **Code Comments**: Some modules lack comprehensive comments.

## Best Practices

1. **Environment Variables**: Use environment variables for configuration, not hardcoded values.

2. **Database Migrations**: Use Alembic for database migrations instead of `Base.metadata.create_all()`.

3. **Type Hints**: Use type hints consistently throughout the codebase.

4. **Error Handling**: Implement consistent error handling with appropriate HTTP status codes.

5. **Logging**: Use structured logging for better observability.

6. **Security**: Follow security best practices for authentication and data protection.

7. **Testing**: Write comprehensive tests for all functionality.

8. **Documentation**: Keep documentation up-to-date with code changes.

## Conclusion

The Mantra Demo application provides a solid foundation for Google OAuth integration. By addressing the known issues and following best practices, it can be enhanced into a production-ready application.
