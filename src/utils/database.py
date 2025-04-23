"""
Database configuration and session management.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from src.models.base import Base
from src.models.users import Users
from src.models.google_integration import GoogleIntegration

# Load environment variables
load_dotenv()

# Use SQLite database
DATABASE_URL = "sqlite:///./mantra.db"

# Create SQLAlchemy engine
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# Create all tables
Base.metadata.create_all(bind=engine)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """
    Dependency to get database session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 