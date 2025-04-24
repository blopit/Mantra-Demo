"""
Database configuration and session management for the Mantra Demo application.

This module provides:
- Database connection configuration using SQLAlchemy
- Session management for database operations
- Table creation for all defined models
- Dependency function for FastAPI to get database sessions

The application uses SQLite for simplicity, but can be configured to use
other databases by changing the DATABASE_URL.
"""

import os
import uuid
from sqlalchemy import create_engine, TypeDecorator, String
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool, NullPool
from dotenv import load_dotenv
from src.models.base import Base

# Load environment variables from .env file
load_dotenv()  # Ensures environment variables are available

class SQLiteUUID(TypeDecorator):
    """Platform-independent UUID type for SQLite.
    Uses String(32) as underlying type.
    """

    impl = String
    cache_ok = True

    def __init__(self):
        super().__init__(length=32)

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        return str(value).replace('-', '')

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        return uuid.UUID(value)

# Register UUID type for SQLite
from sqlalchemy.dialects import sqlite
sqlite.base.ischema_names['uuid'] = SQLiteUUID

def get_database_url():
    """Get database URL based on environment."""
    # For testing, always use in-memory SQLite
    if os.getenv("TESTING") == "true":
        return "sqlite://"

    # Check environment (development or production)
    env = os.getenv("ENVIRONMENT", os.getenv("ENV", "development")).lower()

    if env == "development":
        # Development mode - prefer DATABASE_URL_DEV if set
        db_url = os.getenv("DATABASE_URL_DEV")
        if db_url:
            # Fix potential newline issues in .env file
            db_url = db_url.split('\n')[0].strip()
            return db_url
        return "sqlite:///mantra_dev.db"  # Default to SQLite for development

    # Production mode - use DATABASE_URL
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        # Fix potential newline issues in .env file
        db_url = db_url.split('\n')[0].strip()
        return db_url

    # Fallback to SQLite if no production URL is set
    return "sqlite:///mantra.db"

def get_engine(database_url=None):
    """Get SQLAlchemy engine with optimized configuration."""
    if database_url is None:
        database_url = get_database_url()

    # Get environment variables for configuration
    debug_mode = os.getenv("DEBUG", "False").lower() == "true"
    pool_size = int(os.getenv("POOL_SIZE", "5"))
    max_overflow = int(os.getenv("MAX_OVERFLOW", "10"))
    pool_timeout = int(os.getenv("POOL_TIMEOUT", "30"))
    pool_recycle = int(os.getenv("POOL_RECYCLE", "1800"))  # 30 minutes

    connect_args = {}
    engine_args = {
        "echo": debug_mode,  # Only log SQL in debug mode
        "echo_pool": debug_mode
    }

    if database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
        # For SQLite, use NullPool for in-memory DB or a small pool for file DB
        if database_url == "sqlite://":
            engine_args["poolclass"] = NullPool
        else:
            # For file-based SQLite, a small connection pool is better
            engine_args["pool_size"] = min(pool_size, 3)  # SQLite works better with fewer connections
            engine_args["max_overflow"] = 0  # Prevent overflow connections for SQLite
    else:
        # For PostgreSQL, MySQL, etc., use QueuePool with configured values
        engine_args["poolclass"] = QueuePool
        engine_args["pool_size"] = pool_size
        engine_args["max_overflow"] = max_overflow
        engine_args["pool_timeout"] = pool_timeout
        engine_args["pool_recycle"] = pool_recycle

    return create_engine(
        database_url,
        connect_args=connect_args,
        **engine_args
    )

def get_session_local(engine=None):
    """Get SQLAlchemy session factory with optimized settings."""
    if engine is None:
        engine = get_engine()

    return sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
        expire_on_commit=False  # Performance optimization to prevent unnecessary DB hits
    )

# Create default engine and session factory
engine = get_engine()
SessionLocal = get_session_local(engine)

def get_db():
    """
    Dependency to get database session for FastAPI endpoints.

    This function creates a new database session for each request,
    yields it for use in the endpoint, and ensures it's closed
    when the request is complete, even if an exception occurs.

    Usage:
        @app.get("/users")
        def get_users(db: Session = Depends(get_db)):
            users = db.query(Users).all()
            return users

    Yields:
        Session: SQLAlchemy database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Create all tables - only if not in testing mode and not using migrations
if os.getenv("TESTING") != "true" and os.getenv("USE_MIGRATIONS", "False").lower() != "true":
    Base.metadata.create_all(bind=engine)