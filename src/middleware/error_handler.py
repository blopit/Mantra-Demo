"""
Error handling middleware for the application.

This module provides centralized error handling for the application,
ensuring consistent error responses across all endpoints.
"""

import logging
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.utils.api_response import error_response
from src.exceptions import MantraError, MantraNotFoundError

# Configure logging
logger = logging.getLogger(__name__)


def add_error_handlers(app: FastAPI) -> None:
    """
    Add error handlers to the FastAPI application.
    
    Args:
        app: FastAPI application instance
    """
    
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        """Handle HTTP exceptions."""
        logger.warning(f"HTTP exception: {exc.detail} (status_code={exc.status_code})")
        return JSONResponse(
            content=error_response(
                message=exc.detail,
                code="http_error",
                status_code=exc.status_code
            ),
            status_code=exc.status_code
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        """Handle request validation errors."""
        errors = exc.errors()
        error_messages = []
        
        for error in errors:
            loc = " -> ".join(str(loc_item) for loc_item in error["loc"])
            msg = f"{loc}: {error['msg']}"
            error_messages.append(msg)
        
        error_msg = "Validation error"
        logger.warning(f"{error_msg}: {', '.join(error_messages)}")
        
        return JSONResponse(
            content=error_response(
                message=error_msg,
                code="validation_error",
                details={"errors": error_messages}
            ),
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
        )
    
    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
        """Handle database errors."""
        error_msg = "Database error occurred"
        logger.error(f"Database error: {str(exc)}")
        
        return JSONResponse(
            content=error_response(
                message=error_msg,
                code="database_error"
            ),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    @app.exception_handler(MantraNotFoundError)
    async def mantra_not_found_handler(request: Request, exc: MantraNotFoundError) -> JSONResponse:
        """Handle mantra not found errors."""
        error_msg = str(exc) or "Mantra not found"
        logger.warning(f"Mantra not found: {error_msg}")
        
        return JSONResponse(
            content=error_response(
                message=error_msg,
                code="mantra_not_found"
            ),
            status_code=status.HTTP_404_NOT_FOUND
        )
    
    @app.exception_handler(MantraError)
    async def mantra_error_handler(request: Request, exc: MantraError) -> JSONResponse:
        """Handle general mantra errors."""
        error_msg = str(exc) or "Error processing mantra"
        logger.error(f"Mantra error: {error_msg}")
        
        return JSONResponse(
            content=error_response(
                message=error_msg,
                code="mantra_error"
            ),
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Handle all other exceptions."""
        error_msg = "An unexpected error occurred"
        logger.error(f"Unexpected error: {str(exc)}", exc_info=True)
        
        return JSONResponse(
            content=error_response(
                message=error_msg,
                code="server_error",
                details={"type": type(exc).__name__}
            ),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
