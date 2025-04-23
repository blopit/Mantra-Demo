"""
Main application entry point.
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

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(title="Mantra Demo", description="Google Sign-In Demo")

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
    """Render the Google sign-in page"""
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
    """Render the Google sign-in page with status message"""
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

    # Use port 8000
    port = 8000
    host = "0.0.0.0"

    # Run app
    uvicorn.run(
        "app:app",
        host=host,
        port=port,
        reload=True
    )
