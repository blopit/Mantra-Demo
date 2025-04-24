"""
Base model configuration for SQLAlchemy ORM.

This module defines the base declarative class that all model classes
will inherit from. It provides the foundation for SQLAlchemy's ORM
functionality throughout the application.

Usage:
    from src.models.base import Base

    class MyModel(Base):
        __tablename__ = "my_table"

        id = Column(Integer, primary_key=True)
        name = Column(String)
"""

from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()