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

## Environment Management

Switch between development and production environments:

```bash
# Switch to development environment (SQLite)
python scripts/switch_env.py development

# Switch to production environment (PostgreSQL/Supabase)
python scripts/switch_env.py production

# Test current database connection
python scripts/switch_env.py test
```

## Testing

Run the test suite:

```bash
# Run all tests
python scripts/run_tests.py

# Run only unit tests
python scripts/run_tests.py --unit

# Run only integration tests
python scripts/run_tests.py --integration

# Generate coverage report
python scripts/run_tests.py --coverage
```

## Documentation

Detailed documentation is available in the `docs` directory:

- [Architecture](docs/architecture.md)
- [API Routes](docs/routes/api_routes.md)
- [Google Providers](docs/providers/google.md)
- [Testing](docs/testing.md)

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
