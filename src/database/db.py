"""
Database configuration and session management.

This module provides the SQLAlchemy engine, session factory, and dependency
for FastAPI to inject database sessions into route handlers.
"""

import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from src.models.base import Base

# Configure logging
logger = logging.getLogger(__name__)

# Get database URL from environment variable or use SQLite as default
DATABASE_URL = os.getenv("DATABASE_URL")

# If no DATABASE_URL is provided or if it's invalid, fallback to SQLite
if not DATABASE_URL or "supabase" in DATABASE_URL.lower():
    logger.info("Using SQLite database")
    DATABASE_URL = "sqlite:///mantra.db"

# Create SQLAlchemy engine with appropriate connection arguments
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)

# Create all tables in the database
Base.metadata.create_all(bind=engine)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Session:
    """
    FastAPI dependency that provides a database session.
    
    Yields:
        Session: SQLAlchemy database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 