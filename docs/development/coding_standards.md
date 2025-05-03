# Coding Standards

This document outlines the coding standards and best practices for the Mantra Demo project.

## General Principles

1. **Readability**: Code should be easy to read and understand
2. **Simplicity**: Prefer simple solutions over complex ones
3. **Consistency**: Follow established patterns and conventions
4. **Testability**: Write code that is easy to test
5. **Documentation**: Document code appropriately

## Python Style Guide

### PEP 8

Follow the [PEP 8](https://www.python.org/dev/peps/pep-0008/) style guide with the following specifics:

- **Indentation**: 4 spaces (no tabs)
- **Line Length**: Maximum of 88 characters (as per Black formatter)
- **Imports**: Group imports in the following order:
  1. Standard library imports
  2. Related third-party imports
  3. Local application/library specific imports
- **Whitespace**: Follow PEP 8 guidelines for whitespace
- **Comments**: Use comments sparingly and only when necessary
- **Naming Conventions**:
  - Classes: `CamelCase`
  - Functions and variables: `snake_case`
  - Constants: `UPPER_CASE_WITH_UNDERSCORES`
  - Private attributes: `_leading_underscore`

### Type Hints

Use type hints for function parameters and return values:

```python
def get_user_by_id(user_id: str) -> Optional[User]:
    """Get a user by ID."""
    return db.query(User).filter(User.id == user_id).first()
```

### Docstrings

Use Google-style docstrings:

```python
def function_with_types_in_docstring(param1: int, param2: str) -> bool:
    """Example function with types documented in the docstring.
    
    Args:
        param1: The first parameter.
        param2: The second parameter.
    
    Returns:
        True if successful, False otherwise.
        
    Raises:
        ValueError: If param1 is negative.
    """
    if param1 < 0:
        raise ValueError("param1 must be positive")
    return True
```

## Code Organization

### Project Structure

Follow the established project structure:

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
```

### Module Organization

- Each module should have a single responsibility
- Keep modules small and focused
- Use `__init__.py` files to expose public interfaces

## Code Quality Tools

### Black

The project uses [Black](https://black.readthedocs.io/) for code formatting:

```bash
black src tests
```

### isort

The project uses [isort](https://pycqa.github.io/isort/) for import sorting:

```bash
isort src tests
```

### flake8

The project uses [flake8](https://flake8.pycqa.org/) for linting:

```bash
flake8 src tests
```

### mypy

The project uses [mypy](https://mypy.readthedocs.io/) for type checking:

```bash
mypy src
```

## Testing Standards

### Test Organization

- Tests should mirror the structure of the source code
- Use descriptive test names that explain what is being tested
- Follow the AAA (Arrange, Act, Assert) pattern

### Test Naming

- Test files should be named `test_*.py`
- Test classes should be named `Test*`
- Test methods should be named `test_*`

### Test Coverage

- Aim for high test coverage, but prioritize meaningful tests over coverage percentage
- Use pytest-cov to measure coverage:

```bash
python tests/scripts/run_tests.py --coverage
```

### Test Types

- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test how components work together
- **End-to-End Tests**: Test the complete application flow

## Git Workflow

### Branching Strategy

- `main`: Production-ready code
- `develop`: Latest development changes
- Feature branches: `feature/your-feature-name`
- Bug fix branches: `fix/your-bug-fix`
- Release branches: `release/vX.Y.Z`

### Commit Messages

Follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

Types:
- `feat`: A new feature
- `fix`: A bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code changes that neither fix bugs nor add features
- `test`: Adding or updating tests
- `chore`: Changes to the build process or auxiliary tools

### Pull Requests

- Keep pull requests small and focused
- Include tests for new features and bug fixes
- Update documentation as necessary
- Ensure all checks pass before merging

## Documentation Standards

### Code Documentation

- Document all public modules, classes, and functions
- Use docstrings for API documentation
- Add comments for complex logic

### Project Documentation

- Keep documentation up-to-date with code changes
- Use Markdown for documentation files
- Organize documentation in a logical structure

## Security Best Practices

- Never commit sensitive information (API keys, passwords, etc.)
- Use environment variables for configuration
- Validate all user input
- Use parameterized queries to prevent SQL injection
- Follow the principle of least privilege

## Performance Considerations

- Use async/await for I/O-bound operations
- Optimize database queries
- Use caching where appropriate
- Profile code to identify bottlenecks

## Accessibility

- Ensure web interfaces are accessible
- Follow WCAG 2.1 guidelines
- Test with screen readers and keyboard navigation

## Further Reading

- [PEP 8](https://www.python.org/dev/peps/pep-0008/): Style Guide for Python Code
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [WCAG 2.1](https://www.w3.org/TR/WCAG21/)
