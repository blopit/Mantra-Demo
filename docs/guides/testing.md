# Testing Guide

This guide explains how to write and run tests for the Mantra Demo application.

## Overview

The application uses pytest for testing. Tests are organized into three categories:

- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test how components work together
- **End-to-End Tests**: Test the complete application flow

## Test Structure

```
tests/
├── README.md                 # Testing guide
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

### Python Tests

The project includes a dedicated test runner script at `tests/scripts/run_tests.py`.

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

## Writing Tests

### Unit Tests

Unit tests focus on testing individual components in isolation. They are located in the `tests/unit/` directory and are marked with the `@pytest.mark.unit` decorator.

Example unit test:

```python
import pytest
from src.utils.google_credentials import get_credentials_from_dict

@pytest.mark.unit
def test_get_credentials_from_dict():
    """Test getting credentials from a dictionary."""
    # Arrange
    credentials_dict = {
        "token": "test_token",
        "refresh_token": "test_refresh_token",
        "token_uri": "https://oauth2.googleapis.com/token",
        "client_id": "test_client_id",
        "client_secret": "test_client_secret",
        "scopes": ["https://www.googleapis.com/auth/userinfo.email"]
    }
    
    # Act
    credentials = get_credentials_from_dict(credentials_dict)
    
    # Assert
    assert credentials.token == "test_token"
    assert credentials.refresh_token == "test_refresh_token"
    assert credentials.token_uri == "https://oauth2.googleapis.com/token"
    assert credentials.client_id == "test_client_id"
    assert credentials.client_secret == "test_client_secret"
    assert credentials.scopes == ["https://www.googleapis.com/auth/userinfo.email"]
```

### Integration Tests

Integration tests verify that different components work together correctly. They are located in the `tests/integration/` directory and are marked with the `@pytest.mark.integration` decorator.

Example integration test:

```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

@pytest.mark.integration
async def test_google_auth_flow(client: TestClient, db_session: AsyncSession, monkeypatch):
    """Test the Google authentication flow."""
    # Arrange
    monkeypatch.setattr(
        "src.custom_routes.google.auth.get_authorization_url",
        lambda: "https://accounts.google.com/o/oauth2/auth?..."
    )
    
    # Act
    response = client.get("/api/google/auth")
    
    # Assert
    assert response.status_code == 200
    assert "auth_url" in response.json()
    assert response.json()["auth_url"].startswith("https://accounts.google.com/o/oauth2/auth")
```

### End-to-End Tests

End-to-end tests verify the complete application flow from start to finish. They are located in the `tests/e2e/` directory and are marked with the `@pytest.mark.e2e` decorator.

Example end-to-end test:

```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

@pytest.mark.e2e
async def test_mantra_workflow(client: TestClient, db_session: AsyncSession, test_user, mock_n8n_service):
    """Test the complete mantra workflow."""
    # Arrange
    # Create a test mantra
    mantra_data = {
        "name": "Test Mantra",
        "description": "Test description",
        "workflow_json": {"nodes": [], "connections": {}},
        "is_active": True
    }
    
    # Act
    # Create mantra
    create_response = client.post(
        "/api/mantras",
        json=mantra_data,
        headers={"X-Test-User-Id": test_user.id}
    )
    
    # Assert
    assert create_response.status_code == 201
    mantra_id = create_response.json()["id"]
    
    # Act
    # Install mantra
    install_response = client.post(
        "/api/installations",
        json={"mantra_id": mantra_id},
        headers={"X-Test-User-Id": test_user.id}
    )
    
    # Assert
    assert install_response.status_code == 201
    installation_id = install_response.json()["id"]
    
    # Act
    # Get installation
    get_response = client.get(
        f"/api/installations/{installation_id}",
        headers={"X-Test-User-Id": test_user.id}
    )
    
    # Assert
    assert get_response.status_code == 200
    assert get_response.json()["mantra_id"] == mantra_id
    assert get_response.json()["user_id"] == test_user.id
    assert get_response.json()["is_active"] == True
    
    # Act
    # Uninstall mantra
    delete_response = client.delete(
        f"/api/installations/{installation_id}",
        headers={"X-Test-User-Id": test_user.id}
    )
    
    # Assert
    assert delete_response.status_code == 200
```

## Test Fixtures

Test fixtures are defined in `conftest.py` files. Global fixtures are in the root `conftest.py`, while test-type-specific fixtures are in the respective `conftest.py` files in each test directory.

Example fixtures:

```python
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.testclient import TestClient
from src.models.users import Users
import uuid

@pytest_asyncio.fixture
async def db_session() -> AsyncSession:
    """Create a fresh database session for a test."""
    session = async_session()
    
    try:
        yield session
    finally:
        await session.close()

@pytest.fixture
def test_app(test_user, db_session, mock_n8n_service):
    """Create a test application with authentication."""
    # Override dependencies
    main_app.dependency_overrides[get_db] = lambda: db_session
    main_app.dependency_overrides[get_current_user] = lambda: test_user
    main_app.dependency_overrides[get_n8n_service] = lambda: mock_n8n_service
    
    return main_app

@pytest.fixture
def client(test_app) -> TestClient:
    """Create a test client."""
    return TestClient(test_app)

@pytest_asyncio.fixture
async def test_user(db_session):
    """Create a test user."""
    user_id = str(uuid.uuid4())
    user = Users(
        id=user_id,
        email=f"test_{user_id}@example.com",
        name="Test User",
        is_active=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user
```

## Mocking

The application uses pytest-mock for mocking. Here's an example of mocking an external service:

```python
def test_gmail_service(mocker):
    """Test Gmail service with mocked Google API."""
    # Arrange
    mock_build = mocker.patch("googleapiclient.discovery.build")
    mock_service = mock_build.return_value
    mock_users = mock_service.users.return_value
    mock_messages = mock_users.messages.return_value
    mock_list = mock_messages.list.return_value
    mock_list.execute.return_value = {
        "messages": [
            {"id": "msg1", "threadId": "thread1"},
            {"id": "msg2", "threadId": "thread2"}
        ]
    }
    
    # Act
    result = get_gmail_messages("user_id")
    
    # Assert
    assert len(result) == 2
    assert result[0]["id"] == "msg1"
    assert result[1]["id"] == "msg2"
    
    # Verify mock calls
    mock_build.assert_called_once_with("gmail", "v1", credentials=mocker.ANY)
    mock_users.assert_called_once_with()
    mock_messages.assert_called_once_with()
    mock_list.assert_called_once_with(userId="me", maxResults=10, q=None)
    mock_list.execute.assert_called_once()
```

## Test Coverage

The application uses pytest-cov to measure test coverage. Run tests with the `--coverage` option to generate a coverage report:

```bash
python tests/scripts/run_tests.py --coverage
```

The coverage report will be generated in the `htmlcov` directory. Open `htmlcov/index.html` in your browser to view the report.

## Continuous Integration

Tests are automatically run in the CI pipeline. The configuration is in the `.github/workflows/` directory.

## Best Practices

1. **Follow the AAA Pattern**: Arrange, Act, Assert
2. **Keep Tests Independent**: Tests should not depend on each other
3. **Use Descriptive Names**: Test names should describe what is being tested
4. **Mock External Dependencies**: Use mocks for external services
5. **Test Edge Cases**: Include tests for error conditions and edge cases
6. **Maintain Test Coverage**: Aim for high test coverage

## Further Reading

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio Documentation](https://pytest-asyncio.readthedocs.io/)
- [pytest-cov Documentation](https://pytest-cov.readthedocs.io/)
- [FastAPI Testing Documentation](https://fastapi.tiangolo.com/tutorial/testing/)
