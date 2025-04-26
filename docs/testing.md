# Testing

This document describes the testing approach for the Mantra Demo application.

## Test Structure

The tests are organized in a modular structure:

```
tests/
├── conftest.py
├── fixtures/
│   ├── __init__.py
│   ├── google_fixtures.py
│   └── user_fixtures.py
├── integration/
│   ├── __init__.py
│   ├── test_google_auth.py
│   └── test_mantra_api.py
└── unit/
    ├── __init__.py
    ├── test_google_credentials.py
    └── test_database_config.py
```

## Running Tests

The project includes a dedicated test runner script at `scripts/run_tests.py`.

### Run All Tests

```bash
python scripts/run_tests.py
```

### Run Specific Test Suites

```bash
# Run only unit tests
python scripts/run_tests.py --unit

# Run only integration tests
python scripts/run_tests.py --integration

# Run a specific test file
python scripts/run_tests.py tests/unit/test_google_credentials.py

# Run with verbose output
python scripts/run_tests.py -v

# Generate coverage report
python scripts/run_tests.py --coverage
```

The coverage report will be generated in the `htmlcov` directory. Open `htmlcov/index.html` in your browser to view the report.

## Test Environment

The test runner automatically configures the test environment:

- Sets `TESTING=true` environment variable
- Uses in-memory SQLite database for tests
- Disables migrations for tests

## Test Fixtures

Common test fixtures are defined in `tests/conftest.py` and `tests/fixtures/`:

- Database session fixtures
- User fixtures
- Google integration fixtures
- Authentication fixtures

## Mocking External Services

External services like Google APIs are mocked in tests to avoid making real API calls:

```python
# Example of mocking Google API
@pytest.fixture
def mock_gmail_service(mocker):
    mock_service = mocker.patch("src.providers.google.gmail.service.build")
    mock_service.return_value.users.return_value.messages.return_value.list.return_value.execute.return_value = {
        "messages": [
            {"id": "msg1", "threadId": "thread1"},
            {"id": "msg2", "threadId": "thread2"}
        ]
    }
    return mock_service
```
