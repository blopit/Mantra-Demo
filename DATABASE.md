# Database Configuration Guide

This guide explains how to configure and switch between different database backends (SQLite and PostgreSQL/Supabase) in the Mantra Demo application.

## Overview

The application supports three database environments:

1. **Development**: Uses SQLite by default, but can be configured to use PostgreSQL
2. **Production**: Uses PostgreSQL/Supabase by default, but can fall back to SQLite
3. **Testing**: Always uses an in-memory SQLite database

## Standardized Database Usage

The application now uses a single, standardized database file:

- **Development**: `mantra.db` (SQLite)
- **Production**: PostgreSQL/Supabase database specified by `DATABASE_URL`
- **Testing**: In-memory SQLite database

This standardization ensures that all components of the application use the same database, avoiding data fragmentation and inconsistency.

## Configuration

Database configuration is managed through environment variables in the `.env` file:

```
# Environment (development or production)
ENVIRONMENT=development

# SQLite Configuration (Development)
DATABASE_URL_DEV=sqlite:///mantra.db
SQLITE_PATH=mantra.db

# PostgreSQL Configuration (Production)
DATABASE_URL=postgresql+asyncpg://user:password@host:port/dbname

# Database Pool Configuration (for PostgreSQL)
POOL_SIZE=5
MAX_OVERFLOW=10
POOL_TIMEOUT=30
POOL_RECYCLE=1800
```

### SQLite Configuration

For SQLite, the database URL format is:

```
sqlite:///mantra.db
```

The application will automatically convert this to the async version (`sqlite+aiosqlite:///mantra.db`) if needed.

### PostgreSQL/Supabase Configuration

For PostgreSQL or Supabase, the database URL format is:

```
postgresql+asyncpg://username:password@host:port/dbname
```

For Supabase with SSL, use:

```
postgresql+asyncpg://username:password@host:port/dbname?sslmode=require
```

## Database Migration

If you have multiple database files from previous versions, you can migrate the data to the standardized database using the provided migration script:

```bash
# Run the database migration script
python scripts/migrate_databases.py
```

This script will:
1. Read the list of legacy database files from the `LEGACY_DB_PATHS` environment variable
2. Migrate all tables and data from these databases to the target database (`mantra.db`)
3. Handle conflicts and ensure data integrity during the migration

## Switching Environments

You can switch between development and production environments using the provided utility script:

```bash
# Switch to development environment
python switch_env.py development

# Switch to production environment
python switch_env.py production

# Test the current database connection
python switch_env.py test
```

This script will:
1. Update the `ENVIRONMENT` variable in your `.env` file
2. Test the database connection to ensure it's working
3. Report success or failure

## Connection Pooling

The application automatically configures connection pooling based on the database type:

- **SQLite**:
  - In-memory database: Uses `NullPool` (no pooling)
  - File-based database: Uses a small pool (max 3 connections)

- **PostgreSQL/Supabase**:
  - Uses `QueuePool` with configurable settings:
    - `POOL_SIZE`: Number of connections to keep open (default: 5)
    - `MAX_OVERFLOW`: Maximum number of connections to create beyond pool size (default: 10)
    - `POOL_TIMEOUT`: Seconds to wait for a connection from the pool (default: 30)
    - `POOL_RECYCLE`: Seconds after which a connection is recycled (default: 1800)

## Testing

The application includes tests to verify database configuration:

```bash
# Run database configuration tests
python -m pytest tests/test_database_config.py -v
```

These tests verify that:
1. The correct database URL is selected based on the environment
2. Database engines are configured correctly for each database type
3. Newlines in database URLs are handled properly

## Troubleshooting

If you encounter database connection issues:

1. Verify your database URLs in the `.env` file
2. Run `python switch_env.py test` to test the current connection
3. Check that your PostgreSQL/Supabase credentials are correct
4. Ensure the database exists and is accessible
5. For PostgreSQL, verify that the required extensions are installed

For SSL connection issues with PostgreSQL, try adding `?sslmode=require` to your database URL.
