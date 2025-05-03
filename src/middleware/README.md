# Middleware Components

This directory contains middleware components for the application.

## Error Handler Middleware

The `error_handler.py` module provides centralized error handling for the application. It ensures that all errors are returned in a consistent format across all endpoints.

### Features

- Standardized error response format
- Automatic logging of errors
- Custom exception handlers for different error types
- Consistent HTTP status codes

### Supported Exception Types

- `HTTPException`: FastAPI/Starlette HTTP exceptions
- `RequestValidationError`: Pydantic validation errors
- `SQLAlchemyError`: Database-related errors
- `MantraError` and subclasses: Application-specific errors
- Generic `Exception`: Catch-all for unexpected errors

### Usage

The error handlers are registered with the FastAPI application in `app.py`:

```python
from src.middleware.error_handler import add_error_handlers

# Create FastAPI app
app = FastAPI()

# Add error handling middleware
add_error_handlers(app)
```

### Error Response Format

All errors are returned in the following format:

```json
{
  "success": false,
  "error": {
    "message": "Human-readable error message",
    "code": "error_code",
    "details": {
      // Optional additional error details
    }
  }
}
```

### Custom Exceptions

To add custom exception handling, define your exception class in `src.exceptions` and add a handler in `error_handler.py`.

Example:

```python
# In src/exceptions.py
class CustomError(Exception):
    """Custom application error."""
    pass

# In src/middleware/error_handler.py
@app.exception_handler(CustomError)
async def custom_error_handler(request: Request, exc: CustomError) -> JSONResponse:
    """Handle custom errors."""
    error_msg = str(exc) or "A custom error occurred"
    logger.error(f"Custom error: {error_msg}")
    
    return JSONResponse(
        content=error_response(
            message=error_msg,
            code="custom_error"
        ),
        status_code=status.HTTP_400_BAD_REQUEST
    )
```
