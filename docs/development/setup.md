# Development Setup Guide

This guide will help you set up your development environment for the Mantra Demo application.

## Prerequisites

Before you begin, make sure you have the following installed:

- **Python 3.9+**: The application is built with Python 3.9+
- **pip**: Python package manager
- **Git**: Version control system
- **Node.js**: For frontend development (optional)
- **PostgreSQL**: For production database (optional, SQLite is used for development)

## Step 1: Clone the Repository

```bash
git clone https://github.com/yourusername/Mantra-Demo.git
cd Mantra-Demo
```

## Step 2: Set Up a Virtual Environment

It's recommended to use a virtual environment to isolate dependencies:

```bash
# Create a virtual environment
python -m venv .venv

# Activate the virtual environment
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate
```

## Step 3: Install Dependencies

```bash
# Install production dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements-dev.txt
```

## Step 4: Configure Environment Variables

Create a `.env` file based on the template:

```bash
cp .env.template .env
```

Edit the `.env` file with your configuration:

```
# Application Settings
APP_NAME=Mantra Demo
DEBUG=true
ENVIRONMENT=development
PORT=8000
HOST=0.0.0.0
LOG_LEVEL=INFO

# Security
SESSION_SECRET_KEY=generate_a_secure_random_key_here
CORS_ORIGINS=http://localhost:8000,http://localhost:3000

# Database Configuration
DATABASE_URL=sqlite:///sqlite.db

# Google OAuth Configuration
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/api/google/callback
GOOGLE_AUTH_SCOPES=https://www.googleapis.com/auth/userinfo.email,https://www.googleapis.com/auth/userinfo.profile,https://www.googleapis.com/auth/gmail.readonly,https://www.googleapis.com/auth/calendar.readonly

# n8n Cloud Configuration
N8N_API_URL=https://your-instance.app.n8n.cloud/api/v1
N8N_WEBHOOK_URL=https://your-instance.app.n8n.cloud
N8N_API_KEY=your_n8n_api_key
N8N_API_TIMEOUT=30.0
N8N_MAX_RETRIES=3
N8N_RETRY_DELAY=1.0
```

## Step 5: Set Up Google OAuth Credentials

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Navigate to "APIs & Services" > "Credentials"
4. Click "Create Credentials" > "OAuth client ID"
5. Select "Web application" as the application type
6. Add "http://localhost:8000/api/google/callback" as an authorized redirect URI
7. Copy the Client ID and Client Secret to your `.env` file

## Step 6: Set Up the Database

The application uses SQLAlchemy with Alembic for database migrations:

```bash
# Create the database tables
alembic upgrade head
```

## Step 7: Set Up Pre-commit Hooks (Optional)

Pre-commit hooks help ensure code quality:

```bash
# Install pre-commit
pip install pre-commit

# Install the git hooks
pre-commit install
```

## Step 8: Run the Application

```bash
# Run the application
python app.py
```

The application will be available at http://localhost:8000

## Step 9: Run Tests

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

## Development Tools

### Code Formatting

The project uses Black for code formatting:

```bash
# Format code
black src tests
```

### Import Sorting

The project uses isort for import sorting:

```bash
# Sort imports
isort src tests
```

### Linting

The project uses flake8 for linting:

```bash
# Lint code
flake8 src tests
```

### Type Checking

The project uses mypy for type checking:

```bash
# Type check code
mypy src
```

### Running All Checks

You can run all checks at once:

```bash
# Run all checks
black src tests && isort src tests && flake8 src tests && mypy src
```

## Switching Between Development and Production

The application supports both SQLite (development) and PostgreSQL (production) databases:

```bash
# Switch to development environment (SQLite)
python scripts/switch_env.py development

# Switch to production environment (PostgreSQL)
python scripts/switch_env.py production

# Test current database connection
python scripts/switch_env.py test
```

## Troubleshooting

### Common Issues

1. **Database connection errors**:
   - Check that your database URL is correct
   - For PostgreSQL, make sure the database server is running

2. **Google OAuth errors**:
   - Verify that your redirect URI matches exactly what's configured in Google Cloud Console
   - Check that your client ID and client secret are correct

3. **Import errors**:
   - Make sure your virtual environment is activated
   - Check that all dependencies are installed

### Getting Help

If you encounter any issues, please:

1. Check the existing issues on GitHub
2. Create a new issue if your problem isn't already reported
3. Provide detailed information about your environment and the steps to reproduce the issue

## Further Reading

- [Coding Standards](coding_standards.md): Guidelines for code style and quality
- [Testing Guide](../guides/testing.md): How to write and run tests
- [Database Configuration](../guides/database_config.md): How to configure different database backends
