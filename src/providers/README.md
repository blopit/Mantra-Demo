# Providers Directory

This directory contains modular provider implementations for various external services.

## Structure

Each provider is organized in its own subdirectory with a consistent structure:

```
providers/
├── google/
│   ├── __init__.py
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── manager.py
│   │   └── credentials.py
│   ├── gmail/
│   │   ├── __init__.py
│   │   ├── adapter.py
│   │   └── service.py
│   ├── calendar/
│   │   ├── __init__.py
│   │   ├── adapter.py
│   │   └── service.py
│   ├── common/
│   │   └── __init__.py
│   └── helpers.py
├── microsoft/
└── ...
```

## Usage

Import provider components directly from their respective modules:

```python
# Import Google services
from src.providers.google import GoogleAuthManager, GmailService, GoogleCredentialsManager

# Initialize services
auth_manager = GoogleAuthManager()
gmail_service = GmailService()
credentials_manager = GoogleCredentialsManager()
```

## Transition from Integrations

The `providers` directory is the new standard for organizing external service integrations. 
Code is being migrated from the legacy `src/integrations` directory to this more modular structure.

Benefits of the new structure:
- Better separation of concerns
- More consistent API design
- Improved testability
- Easier to add new providers
- Clearer dependency management
