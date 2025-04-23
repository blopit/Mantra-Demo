# TODO List for Mantra Demo

This document tracks pending tasks, improvements, and known issues in the Mantra Demo project.

## High Priority

### Security

- [ ] **Remove hardcoded user ID** in `src/custom_routes/google/auth.py` and implement proper authentication
- [ ] **Implement token encryption** for OAuth tokens stored in the database
- [ ] **Use secure session configuration** in production environments
- [ ] **Add rate limiting** to prevent abuse of authentication endpoints
- [ ] **Implement CSRF protection** for all forms and state-changing requests

### Code Structure

- [ ] **Consolidate route duplication** between `src/custom_routes` and `src/routes` directories
- [ ] **Centralize authentication logic** into a single module
- [ ] **Standardize error handling** across all endpoints
- [ ] **Implement proper input validation** for all endpoints

## Medium Priority

### Testing

- [ ] **Increase test coverage** to at least 80%
- [ ] **Add more integration tests** for the complete authentication flow
- [ ] **Add unit tests** for utility functions
- [ ] **Implement mock services** for testing Google API interactions

### Documentation

- [ ] **Add Swagger/OpenAPI documentation** for all endpoints
- [ ] **Create API reference documentation** with examples
- [ ] **Add inline code comments** for complex logic
- [ ] **Create architecture diagrams** for better understanding of the system

### Performance

- [ ] **Optimize database queries** to reduce load times
- [ ] **Implement caching** for frequently accessed data
- [ ] **Add database connection pooling** for better resource utilization

## Low Priority

### Features

- [ ] **Add support for additional Google services** (Drive, Sheets, etc.)
- [ ] **Implement user management** with roles and permissions
- [ ] **Add support for other OAuth providers** (Microsoft, GitHub, etc.)
- [ ] **Create a dashboard** for managing integrations
- [ ] **Add logging to file** for better debugging in production

### Code Quality

- [ ] **Refactor long functions** into smaller, more focused ones
- [ ] **Add type hints** to all functions and methods
- [ ] **Implement consistent naming conventions** across the codebase
- [ ] **Remove unused imports and variables**
- [ ] **Add pre-commit hooks** for code quality checks

### DevOps

- [ ] **Set up CI/CD pipeline** for automated testing and deployment
- [ ] **Create Docker configuration** for containerized deployment
- [ ] **Implement database migrations** with Alembic
- [ ] **Add monitoring and alerting** for production environments
- [ ] **Create deployment documentation** for various environments

## Technical Debt

- [ ] **Replace SQLite with a production database** (PostgreSQL, MySQL)
- [ ] **Upgrade dependencies** to latest versions
- [ ] **Refactor credential storage** to use a more secure approach
- [ ] **Improve error messages** for better user experience
- [ ] **Standardize logging format** across all modules

## Completed Tasks

- [x] Add basic documentation to README.md
- [x] Set up basic project structure
- [x] Implement Google OAuth flow
- [x] Create database models
- [x] Add basic tests

## Notes

- The current implementation is a proof of concept and not production-ready
- Security should be the top priority before deploying to production
- Code duplication should be addressed to improve maintainability
