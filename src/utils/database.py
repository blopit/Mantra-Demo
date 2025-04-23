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
from sqlalchemy import create_engine, TypeDecorator, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from dotenv import load_dotenv
import uuid
from src.models.base import Base
from src.models.users import Users
from src.models.google_integration import GoogleIntegration

# Load environment variables from .env file
load_dotenv()  # Ensures environment variables are available

# Base class for all models
Base = declarative_base()

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
    """Get database URL from environment or use default."""
    if os.getenv("TESTING") == "true":
        return "sqlite://"
    
    return os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/postgres"
    )

def get_engine(database_url=None):
    """Get SQLAlchemy engine."""
    if database_url is None:
        database_url = get_database_url()
    
    connect_args = {}
    if database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
        return create_engine(
            database_url,
            connect_args=connect_args,
            poolclass=StaticPool,
            echo=True
        )
    
    return create_engine(
        database_url,
        connect_args=connect_args,
        echo=True
    )

def get_session_local(engine=None):
    """Get SQLAlchemy session factory."""
    if engine is None:
        engine = get_engine()
    
    return sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine
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

# Create all tables
if os.getenv("TESTING") != "true":
    Base.metadata.create_all(bind=engine)