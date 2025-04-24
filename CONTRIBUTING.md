# Contributing to Mantra Demo

Thank you for considering contributing to Mantra Demo! This document provides guidelines and instructions for contributing to the project.

## Code of Conduct

Please be respectful and considerate of others when contributing to this project. We aim to foster an inclusive and welcoming community.

## How to Contribute

### Reporting Bugs

If you find a bug, please create an issue with the following information:

1. A clear, descriptive title
2. Steps to reproduce the bug
3. Expected behavior
4. Actual behavior
5. Screenshots (if applicable)
6. Environment details (OS, browser, etc.)

### Suggesting Enhancements

If you have an idea for an enhancement, please create an issue with the following information:

1. A clear, descriptive title
2. A detailed description of the enhancement
3. Why this enhancement would be useful
4. Any implementation ideas you have

### Pull Requests

1. Fork the repository
2. Create a new branch for your feature or bug fix
3. Make your changes
4. Add or update tests as necessary
5. Ensure all tests pass
6. Update documentation as necessary
7. Submit a pull request

## Development Setup

### Prerequisites

- Python 3.9 or higher
- pip
- Git

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/Mantra-Demo.git
   cd Mantra-Demo
   ```

2. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file based on `.env.example`:
   ```bash
   cp .env.example .env
   ```

5. Edit the `.env` file with your Google OAuth credentials

### Running the Application

```bash
python app.py
```

The application will be available at http://localhost:8000

### Running Tests

```bash
./run_tests.py
```

## Coding Standards

### Python Style Guide

- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) style guide
- Use 4 spaces for indentation
- Maximum line length of 88 characters
- Use docstrings for all modules, classes, and functions

### Documentation

- Update documentation when changing code
- Use clear, descriptive variable and function names
- Add comments for complex logic

### Testing

- Write tests for all new features and bug fixes
- Maintain or improve test coverage
- Tests should be fast and independent

## Git Workflow

1. Create a branch for your feature or bug fix
   ```bash
   git checkout -b feature/your-feature-name
   ```
   or
   ```bash
   git checkout -b fix/your-bug-fix
   ```

2. Make your changes and commit them with clear, descriptive messages
   ```bash
   git commit -m "Add feature: your feature description"
   ```
   or
   ```bash
   git commit -m "Fix: your bug fix description"
   ```

3. Push your branch to your fork
   ```bash
   git push origin feature/your-feature-name
   ```

4. Create a pull request from your branch to the main repository

## Code Review Process

1. All pull requests require at least one review before merging
2. Address all review comments
3. Ensure all tests pass
4. Update documentation as necessary

## License

By contributing to this project, you agree that your contributions will be licensed under the project's [MIT License](LICENSE).

## Questions?

If you have any questions, please feel free to create an issue or contact the maintainers.

Thank you for contributing to Mantra Demo!
