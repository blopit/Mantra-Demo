"""
Custom SQLAlchemy types for database compatibility across different database engines.

This module provides custom type implementations that work consistently across
different database backends (SQLite, PostgreSQL, etc.) while maintaining
proper data representation and conversion.
"""

from sqlalchemy.types import TypeDecorator, String
from sqlalchemy.dialects.postgresql import UUID
import uuid

class UUIDType(TypeDecorator):
    """
    Platform-independent UUID type for SQLAlchemy models.

    This type automatically adapts to the database being used:
    - For PostgreSQL: Uses the native UUID type
    - For other databases (SQLite, MySQL, etc.): Uses String(36)

    The type handles conversion between Python's uuid.UUID objects and
    the database representation in both directions, ensuring consistent
    behavior regardless of the database backend.

    Usage:
        ```python
        from src.models.custom_types import UUIDType

        class MyModel(Base):
            __tablename__ = "my_table"

            id = Column(UUIDType, primary_key=True, default=uuid4)
            related_id = Column(UUIDType, ForeignKey("other_table.id"))
        ```
    """

    impl = String
    cache_ok = True

    def load_dialect_impl(self, dialect):
        """
        Return a dialect-specific implementation for this type.

        Args:
            dialect: The SQLAlchemy dialect being used

        Returns:
            A dialect-specific type descriptor (UUID for PostgreSQL, String for others)
        """
        if dialect.name == 'postgresql':
            # Use native UUID type for PostgreSQL
            return dialect.type_descriptor(UUID())
        else:
            # Use String(36) for other databases (SQLite, MySQL, etc.)
            return dialect.type_descriptor(String(36))

    def process_bind_param(self, value, dialect):
        """
        Process the value before it is bound to a statement.

        This converts Python values to the appropriate database format.

        Args:
            value: The value to convert (uuid.UUID or string)
            dialect: The SQLAlchemy dialect being used

        Returns:
            The converted value ready for database storage
        """
        if value is None:
            # Pass None values through unchanged
            return value
        elif dialect.name == 'postgresql':
            # PostgreSQL can handle UUID objects, but convert to string if needed
            return str(value) if isinstance(value, uuid.UUID) else value
        else:
            # For other databases, ensure we have a string representation
            if not isinstance(value, uuid.UUID):
                # If it's a string, convert to UUID first to validate format
                return str(uuid.UUID(value))
            # Convert UUID object to string
            return str(value)

    def process_result_value(self, value, dialect):
        """
        Process the value when it is loaded from the database.

        This converts database values to Python uuid.UUID objects.

        Args:
            value: The database value (typically a string)
            dialect: The SQLAlchemy dialect being used

        Returns:
            uuid.UUID object or None
        """
        if value is None:
            # Pass None values through unchanged
            return value
        else:
            # Convert string representation to UUID object
            return uuid.UUID(value)