"""
Main application entry point for the Mantra Demo application.

This module initializes and configures the FastAPI application, including:
- Environment variable loading
- Logging configuration
- Middleware setup (CORS, Sessions)
- Template and static file configuration
- Route registration
- Basic endpoints for the application

The application demonstrates Google OAuth integration with credential storage
in both database and environment variables.
"""

import os
import logging
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv
from sqlalchemy.orm import Session

# Load environment variables from .env file
load_dotenv()  # This loads variables from .env into os.environ

# Configure logging with basic configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app with metadata for OpenAPI documentation
app = FastAPI(
    title="Mantra Demo",
    description="Google Sign-In Demo with credential storage in database and environment variables",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Configure middleware
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET_KEY", "dev-secret-key"),
    max_age=3600,
    same_site="lax",  # Allow session cookies in redirects
    https_only=False  # Allow HTTP in development
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "http://localhost:8000").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Configure templates and static files
templates = Jinja2Templates(directory="src/templates")
app.mount("/static", StaticFiles(directory="src/static"), name="static")

# Import routes
from src.custom_routes.google.auth import router as google_auth_router

# Register routes
app.include_router(google_auth_router)

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """
    Render the Google sign-in page.

    This is the main entry point for users to start the Google OAuth flow.

    Args:
        request (Request): The FastAPI request object

    Returns:
        TemplateResponse: Rendered HTML template for Google sign-in
    """
    return templates.TemplateResponse(
        "google_signin.html",
        {"request": request}
    )

@app.get("/signin", response_class=HTMLResponse)
async def signin(
    request: Request,
    status: str = None,
    success: bool = False
):
    """
    Render the Google sign-in page with status message.

    This endpoint is used for redirects after authentication attempts,
    allowing for status messages to be displayed to the user.

    Args:
        request (Request): The FastAPI request object
        status (str, optional): Status message to display. Defaults to None.
        success (bool, optional): Whether the operation was successful. Defaults to False.

    Returns:
        TemplateResponse: Rendered HTML template with status information
    """
    return templates.TemplateResponse(
        "google_signin.html",
        {
            "request": request,
            "status": status,
            "success": success
        }
    )

if __name__ == "__main__":
    import uvicorn

    # Use port 8000 by default, can be overridden by environment variables
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    reload_enabled = os.getenv("RELOAD", "True").lower() == "true"

    logger.info(f"Starting Mantra Demo application on {host}:{port} (reload={reload_enabled})")

    # Run app with uvicorn server
    uvicorn.run(
        "app:app",
        host=host,
        port=port,
        reload=reload_enabled,
        log_level="info"
    )
