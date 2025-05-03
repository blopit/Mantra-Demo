# System Architecture Overview

## Introduction

Mantra Demo is built with a clean, modular architecture that separates concerns and makes the codebase maintainable and extensible. This document provides an overview of the system architecture.

## Architecture Diagram

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│  Web Interface  │────▶│  FastAPI App    │────▶│  Service Layer  │
│                 │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                         │
                                                         ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│  External APIs  │◀───▶│   Adapters      │◀───▶│  Repositories   │
│  (Google, N8N)  │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                         │
                                                         ▼
                                                ┌─────────────────┐
                                                │                 │
                                                │   Database      │
                                                │                 │
                                                └─────────────────┘
```

## Core Components

### 1. Web Interface

The web interface is built with HTML, CSS, and JavaScript. It provides a user-friendly way to interact with the application.

### 2. FastAPI Application

The FastAPI application handles HTTP requests and responses. It includes:

- **Routes**: Define API endpoints
- **Middleware**: Handle cross-cutting concerns like authentication
- **Dependency Injection**: Provide services and repositories to routes

### 3. Service Layer

The service layer contains the business logic of the application. It:

- Orchestrates operations across multiple repositories
- Implements business rules and validation
- Handles complex operations that span multiple domains

### 4. Repositories

Repositories provide an abstraction over data storage. They:

- Handle CRUD operations for domain entities
- Encapsulate database queries
- Provide a domain-oriented interface for data access

### 5. Adapters

Adapters provide interfaces to external services like:

- Google APIs (Gmail, Calendar)
- N8N workflow automation
- Database systems (SQLite, PostgreSQL)

### 6. Database

The application supports multiple database backends:

- SQLite for development
- PostgreSQL for production

## Data Flow

1. User interacts with the web interface
2. Web interface sends requests to the FastAPI application
3. FastAPI routes the request to the appropriate handler
4. Handler uses services to process the request
5. Services use repositories and adapters to access data and external services
6. Results flow back through the layers to the user

## Authentication Flow

1. User initiates Google OAuth flow
2. Application redirects to Google for authentication
3. Google redirects back with an authorization code
4. Application exchanges the code for access and refresh tokens
5. Tokens are stored securely in the database
6. Application uses tokens to access Google APIs on behalf of the user

## Key Design Principles

1. **Separation of Concerns**: Each component has a single responsibility
2. **Dependency Injection**: Dependencies are provided rather than created
3. **Domain-Driven Design**: Code is organized around business domains
4. **Repository Pattern**: Data access is abstracted behind repositories
5. **Adapter Pattern**: External services are accessed through adapters

## Technology Stack

- **Backend**: FastAPI, SQLAlchemy, Pydantic
- **Database**: SQLite (dev), PostgreSQL (prod)
- **Authentication**: Google OAuth2
- **External Services**: Google APIs, N8N
- **Testing**: Pytest, Playwright
- **Deployment**: Docker, Kubernetes (optional)

## Further Reading

- [Data Models](data_models.md): Detailed information about the data models
- [Authentication Flow](authentication.md): In-depth explanation of the authentication process
- [API Documentation](../api/overview.md): API reference and examples
