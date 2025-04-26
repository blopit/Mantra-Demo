"""
Main application entry point for the Mantra Demo application.

This module initializes and configures the FastAPI application, including:
- Environment variable loading
- Logging configuration
- Middleware setup (CORS, Sessions)
- Template and static file configuration
- Basic endpoints for the application

The application uses localStorage for user management.
"""

import os
import logging
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Mantra Demo",
    description="Google Sign-In Demo with localStorage user management",
    version="0.1.0"
)

# Configure middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development - restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Add session middleware
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET_KEY", "your-secret-key-here"),  # Change this to a secure secret key
    max_age=3600  # Session expiry time in seconds (1 hour)
)

# Configure templates and static files
templates = Jinja2Templates(directory="src/templates")
app.mount("/static", StaticFiles(directory="src/static"), name="static")

# Import and include routes
from src.routes.google_auth_consolidated import router as google_auth_router
from src.routes.mantra import router as mantra_router
app.include_router(google_auth_router)
app.include_router(mantra_router)

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Redirect to accounts if logged in, otherwise show sign-in page"""
    # Check if user is authenticated
    user = request.session.get("user")

    # If user is authenticated and explicitly requesting root, redirect to accounts
    if user and request.url.path == "/":
        return RedirectResponse(url="/accounts", status_code=302)

    # Otherwise show sign-in page
    return templates.TemplateResponse(
        "google_signin.html",
        {
            "request": request,
            "google_client_id": os.getenv("GOOGLE_CLIENT_ID", "")
        }
    )

@app.get("/signin", response_class=HTMLResponse)
async def signin(
    request: Request,
    status: str = None,
    success: bool = False
):
    """Redirect to accounts if logged in, otherwise show sign-in page with status"""
    # Check if user is authenticated
    user = request.session.get("user")
    if user and not status:  # Only redirect if there's no status message to show
        return RedirectResponse(url="/accounts", status_code=302)

    return templates.TemplateResponse(
        "google_signin.html",
        {
            "request": request,
            "google_client_id": os.getenv("GOOGLE_CLIENT_ID", ""),
            "status": status,
            "success": success
        }
    )

@app.get("/accounts", response_class=HTMLResponse)
async def accounts(request: Request):
    """Render the accounts page for authenticated users only"""
    # Check if user is authenticated
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/signin?status=Please sign in to access your account", status_code=302)

    return templates.TemplateResponse(
        "accounts.html",
        {
            "request": request,
            "google_client_id": os.getenv("GOOGLE_CLIENT_ID", "")
        }
    )

if __name__ == "__main__":
    import uvicorn

    # Always use port 8000
    port = 8000
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
