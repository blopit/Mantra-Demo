# Mantra-Demo
Demo example for Mantra Integration Manager with Google Sign-In

## Overview
This application demonstrates how to implement Google Sign-In and store the credentials in the DATABASE_URL environment variable. It provides a clean, organized approach to authentication with minimal duplication.

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

- `src/custom_routes/google/auth.py`: Main authentication routes
- `src/utils/google_credentials.py`: Utility functions for working with credentials
- `src/templates/google_signin.html`: Sign-in page with DATABASE_URL option

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
