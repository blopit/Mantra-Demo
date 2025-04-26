"""
Main module for the Mantra Demo API.

This module initializes and configures the FastAPI application for API-only usage.
It's a simplified version of app.py that doesn't include HTML templates or static files.
"""

import os
import logging
from fastapi import FastAPI
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
    title="Mantra Demo API",
    description="API-only version of the Mantra Demo application",
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
    secret_key=os.getenv("SESSION_SECRET_KEY", "your-secret-key-here"),
    max_age=3600  # Session expiry time in seconds (1 hour)
)

# Import and include routes
from src.routes.google_auth_consolidated import router as google_auth_router
from src.routes.mantra import router as mantra_router

app.include_router(google_auth_router)
app.include_router(mantra_router)

@app.get("/")
async def root():
    """API root endpoint."""
    return {
        "message": "Mantra Demo API",
        "version": "0.1.0",
        "status": "online"
    }

if __name__ == "__main__":
    import uvicorn

    # Always use port 8001 for API (different from main app)
    port = int(os.getenv("API_PORT", "8001"))
    host = os.getenv("HOST", "0.0.0.0")
    reload_enabled = os.getenv("RELOAD", "True").lower() == "true"

    logger.info(f"Starting Mantra Demo API on {host}:{port} (reload={reload_enabled})")

    # Run app with uvicorn server
    uvicorn.run(
        "src.main:app",
        host=host,
        port=port,
        reload=reload_enabled,
        log_level="info"
    )