# Mantra Demo

<div align="center">
  <h3>A FastAPI-based Integration Manager with Google Sign-In</h3>
</div>

## 📋 Overview

Mantra Demo is a modern FastAPI application that demonstrates how to build a robust integration platform with Google services. It provides a clean, organized approach to authentication, API integration, and workflow management.

### Key Features

- 🔐 Google OAuth2 authentication flow
- 💾 Secure credential storage in database
- 🔄 Integration with Google services (Gmail, Calendar)
- 📊 N8N workflow integration
- 🗃️ SQLAlchemy ORM with support for SQLite and PostgreSQL
- 🏗️ Clean architecture with separation of concerns

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- pip
- Git
- Node.js (for frontend development)

### Installation

1. **Clone the repository**

```bash
git clone https://github.com/yourusername/Mantra-Demo.git
cd Mantra-Demo
```

2. **Set up a virtual environment**

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

4. **Configure environment variables**

Create a `.env` file based on `.env.template`:

```bash
cp .env.template .env
```

Edit the `.env` file with your Google OAuth credentials:

```
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
SESSION_SECRET_KEY=your-secret-key-here
```

5. **Run the application**

```bash
python app.py
```

Then open your browser to http://localhost:8000

## 🧪 Testing

Run the test suite:

```bash
# Run all tests
python tests/scripts/run_tests.py

# Run only unit tests
python tests/scripts/run_tests.py --unit

# Run only integration tests
python tests/scripts/run_tests.py --integration

# Run only end-to-end tests
python tests/scripts/run_tests.py --e2e

# Generate coverage report
python tests/scripts/run_tests.py --coverage
```

For more details on testing, see the [Testing Guide](docs/guides/testing.md).

## 🔧 Development

### Environment Management

Switch between development and production environments:

```bash
# Switch to development environment (SQLite)
python scripts/switch_env.py development

# Switch to production environment (PostgreSQL/Supabase)
python scripts/switch_env.py production

# Test current database connection
python scripts/switch_env.py test
```

### Using Google Credentials

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

## 📚 Documentation

Comprehensive documentation is available in the `docs` directory:

### Architecture
- [System Architecture](docs/architecture/overview.md)
- [Data Models](docs/architecture/data_models.md)
- [Authentication Flow](docs/architecture/authentication.md)

### API Documentation
- [API Overview](docs/api/overview.md)
- [API Routes](docs/api/routes.md)
- [API Examples](docs/api/examples.md)

### Development Guides
- [Development Setup](docs/development/setup.md)
- [Coding Standards](docs/development/coding_standards.md)
- [Testing Guide](docs/guides/testing.md)

### Integration Guides
- [Google Integration](docs/guides/google_integration.md)
- [N8N Integration](docs/guides/n8n_integration.md)
- [Database Configuration](docs/guides/database_config.md)

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details on how to get started.

### Project Structure

```
mantra-demo/
├── alembic/              # Database migrations
├── docs/                 # Documentation
├── scripts/              # Utility scripts
├── src/                  # Source code
│   ├── adapters/         # External service adapters
│   ├── api/              # API definitions
│   ├── auth/             # Authentication logic
│   ├── models/           # Data models
│   ├── providers/        # Service providers (Google, etc.)
│   ├── routes/           # API routes
│   ├── services/         # Business logic
│   ├── static/           # Static files
│   ├── templates/        # HTML templates
│   └── utils/            # Utility functions
├── tests/                # Test suite
│   ├── unit/             # Unit tests
│   ├── integration/      # Integration tests
│   └── e2e/              # End-to-end tests
├── .env.template         # Environment variables template
├── app.py                # Application entry point
└── README.md             # This file
```

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgements

- [FastAPI](https://fastapi.tiangolo.com/) for the web framework
- [SQLAlchemy](https://www.sqlalchemy.org/) for the ORM
- [Google API](https://developers.google.com/api-client-library/python) for integration capabilities
- [N8N](https://n8n.io/) for workflow automation
