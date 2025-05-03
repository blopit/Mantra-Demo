"""
Standardized API response utilities.

This module provides utility functions for creating consistent API responses
across the application. It ensures that all API endpoints return responses
in a standardized format.
"""

from typing import Any, Dict, Optional, Union
from fastapi import status
from fastapi.responses import JSONResponse


def success_response(
    data: Any = None,
    message: Optional[str] = None,
    status_code: int = status.HTTP_200_OK
) -> Dict[str, Any]:
    """
    Create a standardized success response.

    Args:
        data: The response data
        message: Optional success message
        status_code: HTTP status code (default: 200)

    Returns:
        Dict with standardized success response format
    """
    response = {"success": True}
    
    if data is not None:
        response["data"] = data
        
    if message:
        response["message"] = message
        
    return response


def error_response(
    message: str,
    code: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    status_code: int = status.HTTP_400_BAD_REQUEST
) -> Dict[str, Any]:
    """
    Create a standardized error response.

    Args:
        message: Error message
        code: Optional error code
        details: Optional additional error details
        status_code: HTTP status code (default: 400)

    Returns:
        Dict with standardized error response format
    """
    error = {"message": message}
    
    if code:
        error["code"] = code
        
    if details:
        error["details"] = details
        
    return {
        "success": False,
        "error": error
    }


def create_response(
    success: bool,
    data: Any = None,
    message: Optional[str] = None,
    error_code: Optional[str] = None,
    error_details: Optional[Dict[str, Any]] = None,
    status_code: int = status.HTTP_200_OK
) -> JSONResponse:
    """
    Create a standardized JSONResponse object.

    Args:
        success: Whether the request was successful
        data: The response data (for successful responses)
        message: Success or error message
        error_code: Error code (for error responses)
        error_details: Additional error details (for error responses)
        status_code: HTTP status code

    Returns:
        JSONResponse with standardized format
    """
    if success:
        content = success_response(data, message)
    else:
        content = error_response(message or "An error occurred", error_code, error_details)
        
    return JSONResponse(
        content=content,
        status_code=status_code
    )
