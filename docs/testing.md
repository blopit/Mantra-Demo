# Testing

This document describes the testing approach for the Mantra Demo application.

> **Note:** For detailed information about testing, please refer to the [tests/README.md](../tests/README.md) file.

## Test Structure

The tests are organized in a modular structure:

```
tests/
├── README.md                 # Detailed testing guide
├── conftest.py               # Global pytest configuration and fixtures
├── e2e/                      # End-to-end tests
│   └── test_mantra_workflow.py
├── fixtures/                 # Test fixtures and data
│   ├── n8n_service.py        # N8N service mock
│   └── test_workflow.json    # Sample workflow data
├── integration/              # Integration tests
│   ├── conftest.py           # Integration test configuration
│   ├── test_database_adapters.py
│   ├── test_google_auth.py
│   └── ...
├── scripts/                  # Test runner scripts
│   ├── run-js-tests.sh       # JavaScript/Playwright test runner
│   ├── run_tests.py          # Python test runner
│   └── ...
├── unit/                     # Unit tests
│   ├── test_database_config.py
│   ├── test_google_credentials.py
│   └── ...
└── utils/                    # Test utilities
    └── __init__.py           # Common test utilities
```

## Running Tests

The project includes dedicated test runner scripts in the `tests/scripts/` directory.

### Python Tests

```bash
# Run all tests
python tests/scripts/run_tests.py

# Run only unit tests
python tests/scripts/run_tests.py --unit

# Run only integration tests
python tests/scripts/run_tests.py --integration

# Run only end-to-end tests
python tests/scripts/run_tests.py --e2e

# Run a specific test file
python tests/scripts/run_tests.py tests/unit/test_google_credentials.py

# Run with verbose output
python tests/scripts/run_tests.py -v

# Generate coverage report
python tests/scripts/run_tests.py --coverage
```

### JavaScript/Playwright Tests

```bash
# Run all JavaScript tests
bash tests/scripts/run-js-tests.sh

# Run tests with a specific reporter
bash tests/scripts/run-js-tests.sh --reporter=dot

# Run tests without showing the report
bash tests/scripts/run-js-tests.sh --no-report
```

## Test Types

- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Verify that different components work together correctly
- **End-to-End Tests**: Verify the complete application flow from start to finish

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
- N8N service mocks

## Mocking External Services

External services like Google APIs and N8N are mocked in tests to avoid making real API calls:

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
