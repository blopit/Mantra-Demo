# Testing Guide for Mantra Demo

This directory contains all tests for the Mantra Demo application. The tests are organized in a modular structure to make them easy to run and maintain.

## Test Structure

```
tests/
├── README.md                 # This file
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
│   ├── test_mantra_creation.py
│   ├── test_mantra_service.py
│   ├── test_n8n_connection.py
│   ├── test_n8n_service.py
│   ├── test_n8n_workflow_validation.py
│   ├── test_workflow_creation.py
│   └── test_workflow_simple.py
├── scripts/                  # Test runner scripts
│   ├── run-js-tests.sh       # JavaScript/Playwright test runner
│   ├── run_tests.py          # Python test runner
│   ├── test_n8n_connection.py # N8N connection test script
│   └── test_workflow.py      # Workflow test script
├── unit/                     # Unit tests
│   ├── test_database_config.py
│   ├── test_google_credentials.py
│   ├── test_mantra_installation.py
│   ├── test_n8n_conversion.py
│   └── test_use_credentials.py
└── utils/                    # Test utilities
    └── __init__.py           # Common test utilities
```

## Running Tests

### Python Tests

The project includes a dedicated test runner script at `tests/scripts/run_tests.py`.

#### Run All Tests

```bash
python tests/scripts/run_tests.py
```

#### Run Specific Test Suites

```bash
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

The coverage report will be generated in the `htmlcov` directory. Open `htmlcov/index.html` in your browser to view the report.

### JavaScript/Playwright Tests

For JavaScript and Playwright tests, use the `run-js-tests.sh` script:

```bash
# Run all JavaScript tests
bash tests/scripts/run-js-tests.sh

# Run tests with a specific reporter
bash tests/scripts/run-js-tests.sh --reporter=dot

# Run tests without showing the report
bash tests/scripts/run-js-tests.sh --no-report

# Run specific tests
bash tests/scripts/run-js-tests.sh --path=path/to/tests
```

## Test Types

### Unit Tests

Unit tests focus on testing individual components in isolation. They are located in the `tests/unit/` directory and are marked with the `@pytest.mark.unit` decorator.

### Integration Tests

Integration tests verify that different components work together correctly. They are located in the `tests/integration/` directory and are marked with the `@pytest.mark.integration` decorator.

### End-to-End Tests

End-to-end tests verify the complete application flow from start to finish. They are located in the `tests/e2e/` directory and are marked with the `@pytest.mark.e2e` decorator.

## Test Environment

The test runner automatically configures the test environment:

- Sets `TESTING=true` environment variable
- Uses an in-memory SQLite database for tests
- Disables database migrations
- Sets up test fixtures and mocks

## Writing Tests

### Test Naming Conventions

- Test files should be named `test_*.py`
- Test classes should be named `Test*`
- Test methods should be named `test_*`

### Test Fixtures

Common test fixtures are defined in `conftest.py` files. Global fixtures are in the root `conftest.py`, while test-type-specific fixtures are in the respective `conftest.py` files in each test directory.

### Test Utilities

Common test utilities are available in the `tests/utils` module. Import them in your tests as needed:

```python
from tests.utils import load_test_fixture, generate_test_id
```

## Test Fixtures

Test fixtures are located in the `tests/fixtures/` directory. They include:

- `n8n_service.py`: Mock N8N service for testing
- `test_workflow.json`: Sample workflow data for testing

## Continuous Integration

Tests are automatically run in the CI pipeline. The configuration is in the `.github/workflows/` directory.
