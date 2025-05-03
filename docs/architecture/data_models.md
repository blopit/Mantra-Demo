# Data Models

This document describes the data models used in the Mantra Demo application.

## Overview

The application uses SQLAlchemy ORM to define and interact with data models. The models are defined in the `src/models` directory.

## Core Models

### User

The `User` model represents a user of the application.

```python
class Users(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, index=True)
    name = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### Google Auth

The `GoogleAuth` model stores Google OAuth credentials for users.

```python
class GoogleAuth(Base):
    __tablename__ = "google_auth"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"))
    credentials = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### Mantra

The `Mantra` model represents a workflow template.

```python
class Mantra(Base):
    __tablename__ = "mantras"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String)
    description = Column(String)
    workflow_json = Column(JSON)
    user_id = Column(String, ForeignKey("users.id"))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### MantraInstallation

The `MantraInstallation` model represents an instance of a workflow for a specific user.

```python
class MantraInstallation(Base):
    __tablename__ = "mantra_installations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    mantra_id = Column(String, ForeignKey("mantras.id"))
    user_id = Column(String, ForeignKey("users.id"))
    n8n_workflow_id = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

## Relationships

The models have the following relationships:

- A `User` can have multiple `GoogleAuth` records
- A `User` can create multiple `Mantra` workflows
- A `User` can have multiple `MantraInstallation` records
- A `Mantra` can have multiple `MantraInstallation` records

## Database Schema

The database schema is managed using Alembic migrations. The migrations are defined in the `alembic/versions` directory.

## SQLAlchemy Configuration

The SQLAlchemy configuration is defined in `src/utils/database.py`. It supports both SQLite and PostgreSQL databases.

```python
def get_engine():
    """Get SQLAlchemy engine based on environment."""
    database_url = os.getenv("DATABASE_URL", "sqlite:///sqlite.db")
    
    if database_url.startswith("sqlite"):
        # SQLite configuration
        return create_async_engine(
            database_url,
            connect_args={"check_same_thread": False},
            echo=True
        )
    else:
        # PostgreSQL configuration
        return create_async_engine(
            database_url,
            echo=True
        )
```

## Data Access

Data access is abstracted through repository classes in the `src/repositories` directory. These repositories provide methods for CRUD operations on the models.

Example repository:

```python
class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_id(self, user_id: str) -> Optional[Users]:
        result = await self.db.execute(
            select(Users).where(Users.id == user_id)
        )
        return result.scalars().first()
    
    async def get_by_email(self, email: str) -> Optional[Users]:
        result = await self.db.execute(
            select(Users).where(Users.email == email)
        )
        return result.scalars().first()
    
    async def create(self, user: Users) -> Users:
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user
```

## Further Reading

- [Authentication Flow](authentication.md): How authentication data is stored and used
- [Database Configuration](../guides/database_config.md): How to configure different database backends
