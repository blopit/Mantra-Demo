"""
Main application module.

This module initializes and configures the FastAPI application.
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.routes.mantra import router as mantra_router
from src.routes.google import router as google_router
from src.utils.database import init_db, close_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Mantra API",
    description="API for managing mantras and integrations",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(mantra_router, prefix="/api/mantras", tags=["mantras"])
app.include_router(google_router, prefix="/api/google", tags=["google"])

@app.on_event("startup")
async def startup_event():
    """Initialize services on application startup."""
    try:
        logger.info("Starting up application...")
        await init_db()
        logger.info("Application startup complete")
    except Exception as e:
        logger.error(f"Error during startup: {str(e)}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up services on application shutdown."""
    try:
        logger.info("Shutting down application...")
        await close_db()
        logger.info("Application shutdown complete")
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")
        raise

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}