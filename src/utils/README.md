# Utility Functions

This directory contains utility functions used throughout the application.

## API Response Format

The `api_response.py` module provides standardized API response formatting for all endpoints.

### Success Response Format

All successful API responses follow this format:

```json
{
  "success": true,
  "data": {
    // Response data specific to the endpoint
  },
  "message": "Optional success message"
}
```

### Error Response Format

All error responses follow this format:

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

### Common Error Codes

- `validation_error`: Invalid request parameters
- `unauthorized`: Authentication required
- `forbidden`: Insufficient permissions
- `not_found`: Resource not found
- `database_error`: Database-related error
- `server_error`: Internal server error

## Usage

```python
from src.utils.api_response import success_response, error_response
from fastapi.responses import JSONResponse
from fastapi import status

# Success response
@app.get("/api/resource")
async def get_resource():
    data = {"id": 1, "name": "Example"}
    return JSONResponse(
        content=success_response(
            data=data,
            message="Resource retrieved successfully"
        )
    )

# Error response
@app.get("/api/resource/{resource_id}")
async def get_resource_by_id(resource_id: int):
    if resource_id not in resources:
        return JSONResponse(
            content=error_response(
                message=f"Resource with ID {resource_id} not found",
                code="not_found"
            ),
            status_code=status.HTTP_404_NOT_FOUND
        )
    # ...
```
