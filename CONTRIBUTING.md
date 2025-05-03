# Contributing to Mantra Demo

Thank you for considering contributing to Mantra Demo! This document provides guidelines and instructions for contributing to the project.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
  - [Development Environment](#development-environment)
  - [Project Structure](#project-structure)
- [Development Workflow](#development-workflow)
  - [Branching Strategy](#branching-strategy)
  - [Commit Messages](#commit-messages)
  - [Pull Requests](#pull-requests)
- [Coding Standards](#coding-standards)
  - [Python Style Guide](#python-style-guide)
  - [Documentation](#documentation)
  - [Testing](#testing)
- [Issue Reporting](#issue-reporting)
  - [Bug Reports](#bug-reports)
  - [Feature Requests](#feature-requests)
- [Code Review Process](#code-review-process)
- [License](#license)

## Code of Conduct

Please be respectful and considerate of others when contributing to this project. We aim to foster an inclusive and welcoming community.

## Getting Started

### Development Environment

#### Prerequisites

- Python 3.9 or higher
- pip
- Git
- Node.js (for frontend development)

#### Setup

1. **Fork and clone the repository**:
   ```bash
   git clone https://github.com/your-username/Mantra-Demo.git
   cd Mantra-Demo
   ```

2. **Set up a virtual environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # Development dependencies
   ```

4. **Configure environment variables**:
   ```bash
   cp .env.template .env
   ```
   Edit the `.env` file with your Google OAuth credentials and other settings.

5. **Set up pre-commit hooks** (optional but recommended):
   ```bash
   pre-commit install
   ```

### Project Structure

The project follows a modular structure:

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

## Development Workflow

### Branching Strategy

We use a simplified Git flow:

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

Examples:
```
feat(auth): add Google OAuth2 authentication
fix(api): resolve issue with credential storage
docs(readme): update installation instructions
```

### Pull Requests

1. **Create a new branch** from `develop` for your changes:
   ```bash
   git checkout develop
   git pull
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** and commit them with descriptive messages.

3. **Run tests** to ensure your changes don't break existing functionality:
   ```bash
   python tests/scripts/run_tests.py
   ```

4. **Update documentation** if necessary.

5. **Push your branch** to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```

6. **Create a pull request** to the `develop` branch of the main repository.

7. **Address review comments** if any.

## Coding Standards

### Python Style Guide

- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) style guide
- Use 4 spaces for indentation
- Maximum line length of 88 characters (as per Black formatter)
- Use type hints where appropriate
- Use docstrings for all modules, classes, and functions

We use the following tools to enforce coding standards:
- [Black](https://black.readthedocs.io/) for code formatting
- [isort](https://pycqa.github.io/isort/) for import sorting
- [flake8](https://flake8.pycqa.org/) for linting
- [mypy](https://mypy.readthedocs.io/) for type checking

You can run these tools with:
```bash
# Format code
black src tests

# Sort imports
isort src tests

# Lint code
flake8 src tests

# Type check
mypy src
```

### Documentation

- Use [Google-style docstrings](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings)
- Document all public modules, classes, and functions
- Keep documentation up-to-date with code changes
- Use clear, descriptive variable and function names
- Add comments for complex logic

Example:
```python
def get_credentials(user_id: str) -> Dict[str, Any]:
    """
    Retrieve Google OAuth credentials for a user.

    Args:
        user_id: The ID of the user to get credentials for

    Returns:
        A dictionary containing the user's Google OAuth credentials

    Raises:
        CredentialsNotFoundError: If no credentials are found for the user
    """
    # Implementation...
```

### Testing

- Write tests for all new features and bug fixes
- Maintain or improve test coverage
- Tests should be fast and independent
- Follow the AAA (Arrange, Act, Assert) pattern

We use pytest for testing. Run tests with:
```bash
python tests/scripts/run_tests.py
```

## Issue Reporting

### Bug Reports

When reporting a bug, please include:

1. A clear, descriptive title
2. Steps to reproduce the bug
3. Expected behavior
4. Actual behavior
5. Screenshots (if applicable)
6. Environment details (OS, browser, Python version, etc.)

### Feature Requests

When suggesting a feature, please include:

1. A clear, descriptive title
2. A detailed description of the proposed feature
3. Why this feature would be useful
4. Any implementation ideas you have

## Code Review Process

1. All pull requests require at least one review before merging
2. Address all review comments
3. Ensure all tests pass
4. Update documentation as necessary
5. Maintain or improve code coverage

## License

By contributing to this project, you agree that your contributions will be licensed under the project's [MIT License](LICENSE).

---

Thank you for contributing to Mantra Demo! If you have any questions, please feel free to create an issue or contact the maintainers.
