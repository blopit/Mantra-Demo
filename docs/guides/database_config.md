# Database Configuration Guide

This guide explains how to configure and manage the database in the Mantra Demo application.

## Overview

The application supports multiple database backends:

- **SQLite**: For development and testing
- **PostgreSQL**: For production

The database configuration is managed through environment variables and the SQLAlchemy ORM.

## Database Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│  Application    │────▶│  SQLAlchemy     │────▶│  Database       │
│  Code           │     │  ORM            │     │  (SQLite/Postgres)
│                 │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                              │
                              ▼
                        ┌─────────────────┐
                        │                 │
                        │  Alembic        │
                        │  Migrations     │
                        │                 │
                        └─────────────────┘
```

## Database URL Format

The database connection is configured using the `DATABASE_URL` environment variable:

### SQLite

```
DATABASE_URL=sqlite:///sqlite.db
```

### PostgreSQL

```
DATABASE_URL=postgresql+asyncpg://username:password@hostname:port/database
```

## Setting Up the Database

### SQLite (Development)

SQLite is the default database for development. It requires no additional setup:

```bash
# Set the DATABASE_URL environment variable
export DATABASE_URL=sqlite:///sqlite.db

# Or add to .env file
echo "DATABASE_URL=sqlite:///sqlite.db" >> .env
```

### PostgreSQL (Production)

For production, it's recommended to use PostgreSQL:

1. **Install PostgreSQL**:
   ```bash
   # Ubuntu/Debian
   sudo apt-get update
   sudo apt-get install postgresql postgresql-contrib
   
   # macOS with Homebrew
   brew install postgresql
   ```

2. **Create a Database**:
   ```bash
   sudo -u postgres psql
   
   # In the PostgreSQL prompt
   CREATE DATABASE mantra;
   CREATE USER mantra_user WITH PASSWORD 'your_password';
   GRANT ALL PRIVILEGES ON DATABASE mantra TO mantra_user;
   \q
   ```

3. **Configure the Application**:
   ```bash
   # Set the DATABASE_URL environment variable
   export DATABASE_URL=postgresql+asyncpg://mantra_user:your_password@localhost:5432/mantra
   
   # Or add to .env file
   echo "DATABASE_URL=postgresql+asyncpg://mantra_user:your_password@localhost:5432/mantra" >> .env
   ```

## Database Migrations

The application uses Alembic for database migrations:

### Creating the Initial Database

```bash
# Create the database tables
alembic upgrade head
```

### Creating a New Migration

When you make changes to the database models, create a new migration:

```bash
# Create a new migration
alembic revision --autogenerate -m "Description of changes"

# Apply the migration
alembic upgrade head
```

### Rolling Back Migrations

If you need to roll back a migration:

```bash
# Roll back one migration
alembic downgrade -1

# Roll back to a specific revision
alembic downgrade revision_id

# Roll back to the beginning
alembic downgrade base
```

## Switching Between Environments

The application includes a script to switch between development and production environments:

```bash
# Switch to development environment (SQLite)
python scripts/switch_env.py development

# Switch to production environment (PostgreSQL)
python scripts/switch_env.py production

# Test current database connection
python scripts/switch_env.py test
```

## Database Models

The application defines its database models using SQLAlchemy ORM. The models are defined in the `src/models` directory:

### Base Model

```python
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
```

### Example Model

```python
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from src.models.base import Base

class Users(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, index=True)
    name = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

## Database Access

The application provides a dependency injection system for database access:

```python
from src.utils.database import get_db

@router.get("/users/{user_id}")
async def get_user(user_id: str, db: AsyncSession = Depends(get_db)):
    """Get a user by ID."""
    result = await db.execute(
        select(Users).where(Users.id == user_id)
    )
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
```

## Database Repositories

The application uses the repository pattern to abstract database access:

```python
class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_id(self, user_id: str) -> Optional[Users]:
        """Get a user by ID."""
        result = await self.db.execute(
            select(Users).where(Users.id == user_id)
        )
        return result.scalars().first()
    
    async def create(self, user: Users) -> Users:
        """Create a new user."""
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user
```

## Database Adapters

The application provides adapters for different database backends:

```python
from src.adapters.database import DatabaseAdapter
from src.adapters.database.sqlite import SQLiteAdapter
from src.adapters.database.postgres import PostgresAdapter

# Create the appropriate adapter based on the DATABASE_URL
database_url = os.getenv("DATABASE_URL", "sqlite:///sqlite.db")
if database_url.startswith("sqlite"):
    adapter = SQLiteAdapter(database_url)
else:
    adapter = PostgresAdapter(database_url)
```

## Best Practices

1. **Use Migrations**: Always use Alembic migrations to make database changes
2. **Use Transactions**: Wrap database operations in transactions
3. **Handle Errors**: Implement proper error handling for database operations
4. **Use Indexes**: Add indexes to columns that are frequently queried
5. **Optimize Queries**: Write efficient database queries

## Troubleshooting

### Common Issues

1. **Connection Errors**:
   - Check that the database server is running
   - Verify that the DATABASE_URL is correct
   - Check network connectivity

2. **Migration Errors**:
   - Make sure all models are imported in `alembic/env.py`
   - Check for conflicts in migration scripts

3. **Performance Issues**:
   - Add indexes to frequently queried columns
   - Use database profiling tools to identify slow queries

## Further Reading

- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [SQLite Documentation](https://www.sqlite.org/docs.html)
