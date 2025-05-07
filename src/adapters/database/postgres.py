"""
PostgreSQL database adapter.
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

class PostgresAdapter:
    """PostgreSQL database adapter."""

    def __init__(self, database_url: str = None):
        """Initialize the adapter.
        
        Args:
            database_url (str, optional): Database connection URL
        """
        self.database_url = database_url
        self.engine = None
        self.session_factory = None

    async def init(self) -> None:
        """Initialize the database connection."""
        if not self.database_url:
            raise ValueError("Database URL is required")

        # Create async engine
        self.engine = create_async_engine(
            self.database_url,
            echo=True,
            future=True,
            poolclass=NullPool
        )

        # Create async session factory
        self.session_factory = sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )

    async def get_session(self) -> AsyncSession:
        """Get a PostgreSQL database session.

        Returns:
            AsyncSession: A new database session
        """
        if not self.session_factory:
            raise RuntimeError("Database not initialized. Call init() first.")

        return self.session_factory()

    async def close(self):
        """Close the database connection."""
        if self.engine:
            await self.engine.dispose()
            self.engine = None
            self.session_factory = None 