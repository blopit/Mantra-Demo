"""
Database configuration and session management for the Mantra Demo application.

This module provides:
- Database connection configuration using SQLAlchemy
- Session management for database operations
- Table creation for all defined models
- Dependency function for FastAPI to get database sessions

The application supports both SQLite (development) and PostgreSQL (production)
databases through environment configuration.
"""

import os
import uuid
import logging
from sqlalchemy import create_engine, TypeDecorator, String, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import QueuePool, NullPool
from dotenv import load_dotenv
from typing import AsyncGenerator

# Load environment variables from .env file
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

# Import all models to ensure they are registered
from src.models.base import Base
from src.models.users import Users
from src.models.contacts import Contacts
from src.models.google_auth import GoogleAuth
from src.models.google_integration import GoogleIntegration
from src.models.mantra import Mantra, MantraInstallation

from src.adapters.database.factory import DatabaseAdapterFactory

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
    """
    Get database URL based on environment.

    This function determines the appropriate database URL based on the current
    environment (testing, development, or production). It supports seamless
    switching between SQLite and PostgreSQL/Supabase.

    Returns:
        str: Database connection URL
    """
    # For testing, always use in-memory SQLite
    if os.getenv("TESTING", "").lower() == "true":
        logger.info("Using in-memory SQLite database for testing")
        return "sqlite+aiosqlite://"

    # Check environment (development or production)
    env = os.getenv("ENVIRONMENT", os.getenv("ENV", "development")).lower()
    logger.info(f"Current environment: {env}")

    if env == "development":
        # Development mode - prefer DATABASE_URL_DEV if set
        db_url = os.getenv("DATABASE_URL_DEV")
        if db_url:
            # Fix potential newline issues in .env file
            db_url = db_url.split('\n')[0].strip()

            # Convert standard SQLite URL to aiosqlite URL if needed
            if db_url.startswith("sqlite:///") and not db_url.startswith("sqlite+aiosqlite:///"):
                db_url = db_url.replace("sqlite:///", "sqlite+aiosqlite:///")

            db_type = "PostgreSQL" if db_url.startswith("postgresql") else "SQLite"
            logger.info(f"Using {db_type} database for development: {db_url}")
            return db_url

        # Default to SQLite for development
        logger.info("Using default SQLite database for development")
        return "sqlite+aiosqlite:///mantra.db"

    # Production mode - use DATABASE_URL
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        # Fix potential newline issues in .env file
        db_url = db_url.split('\n')[0].strip()
        db_type = "PostgreSQL" if db_url.startswith("postgresql") else "SQLite"
        logger.info(f"Using {db_type} database for production")
        return db_url

    # Fallback to SQLite if no production URL is set
    logger.warning("No DATABASE_URL found, falling back to SQLite for production")
    return "sqlite+aiosqlite:///mantra.db"

def get_engine(database_url=None):
    """
    Get SQLAlchemy engine with optimized configuration.

    This function creates a database engine with optimized settings based on
    the database type (SQLite or PostgreSQL). It applies different connection
    pooling strategies and performance optimizations for each database type.

    Args:
        database_url (str, optional): Database URL. If None, determined from environment.

    Returns:
        Engine: Configured SQLAlchemy engine
    """
    if database_url is None:
        database_url = get_database_url()

    # Get environment variables for configuration
    debug_mode = os.getenv("DEBUG", "False").lower() == "true"

    # Common engine arguments
    connect_args = {}
    engine_args = {
        "echo": debug_mode,  # Only log SQL in debug mode
        "echo_pool": debug_mode
    }

    # Database-specific optimizations
    if database_url.startswith("sqlite"):
        # SQLite-specific optimizations
        connect_args["check_same_thread"] = False
        engine_args["poolclass"] = NullPool
        logger.info("Using NullPool for SQLite database")

    elif database_url.startswith("postgresql"):
        # PostgreSQL-specific optimizations
        pool_size = int(os.getenv("POOL_SIZE", "5"))
        max_overflow = int(os.getenv("MAX_OVERFLOW", "10"))
        pool_timeout = int(os.getenv("POOL_TIMEOUT", "30"))
        pool_recycle = int(os.getenv("POOL_RECYCLE", "1800"))  # 30 minutes

        engine_args.update({
            "poolclass": QueuePool,
            "pool_size": pool_size,
            "max_overflow": max_overflow,
            "pool_timeout": pool_timeout,
            "pool_recycle": pool_recycle,
            "pool_pre_ping": True  # Verify connections before using them
        })
        logger.info(f"Using QueuePool for PostgreSQL database (size={pool_size}, max_overflow={max_overflow})")

    # Create and return the engine
    return create_async_engine(
        database_url,
        connect_args=connect_args,
        **engine_args
    )

def get_session_local(engine=None):
    """
    Get SQLAlchemy session factory with optimized settings.

    This function creates a session factory with performance optimizations
    for the specified database engine.

    Args:
        engine (Engine, optional): SQLAlchemy engine. If None, a new engine is created.

    Returns:
        sessionmaker: Configured SQLAlchemy session factory
    """
    if engine is None:
        engine = get_engine()

    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,  # Performance optimization to prevent unnecessary DB hits
        future=True  # Use SQLAlchemy 2.0 query style for better performance
    )

# Create default engine and session factory
engine = get_engine()
SessionLocal = get_session_local(engine)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get a database session.

    This is a FastAPI dependency that provides a database session
    for route handlers.

    Yields:
        AsyncSession: A database session
    """
    adapter = await DatabaseAdapterFactory.get_adapter()
    session_cm = await adapter.get_session()
    async with session_cm as session:
        try:
            yield session
        finally:
            await session.close()

async def init_db() -> None:
    """Initialize the database connection.

    This function should be called during application startup.
    """
    try:
        environment = os.getenv("ENVIRONMENT", "development").lower()
        logger.info(f"Current environment: {environment}")

        # Log database configuration
        if environment == "development":
            logger.info("Using default SQLite database for development")
            logger.info("Using NullPool for SQLite database")
        else:
            logger.info("Using PostgreSQL database for production/staging")
            logger.info(f"Pool size: {os.getenv('POOL_SIZE', '5')}")
            logger.info(f"Max overflow: {os.getenv('MAX_OVERFLOW', '10')}")

        # Initialize the database adapter
        await DatabaseAdapterFactory.get_adapter()

    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        raise

async def close_db() -> None:
    """Close the database connection.

    This function should be called during application shutdown.
    """
    try:
        await DatabaseAdapterFactory.close_adapter()
        logger.info("Closed database connection")
    except Exception as e:
        logger.error(f"Error closing database connection: {str(e)}")
        raise