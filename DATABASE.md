# Database Configuration Guide

This guide explains how to configure and switch between different database backends (SQLite and PostgreSQL/Supabase) in the Mantra Demo application.

## Overview

The application supports three database environments:

1. **Development**: Uses SQLite by default, but can be configured to use PostgreSQL
2. **Production**: Uses PostgreSQL/Supabase by default, but can fall back to SQLite
3. **Testing**: Always uses an in-memory SQLite database

## Configuration

Database configuration is managed through environment variables in the `.env` file:

```
# Environment (development or production)
ENVIRONMENT=development

# Development database URL (used when ENVIRONMENT=development)
DATABASE_URL_DEV=sqlite:///mantra_dev.db

# Production database URL (used when ENVIRONMENT=production)
DATABASE_URL=postgresql://user:password@host:port/dbname
```

### SQLite Configuration

For SQLite, the database URL format is:

```
sqlite:///path/to/database.db
```

The default SQLite databases are:
- Development: `sqlite:///mantra_dev.db`
- Production: `sqlite:///mantra.db`

### PostgreSQL/Supabase Configuration

For PostgreSQL or Supabase, the database URL format is:

```
postgresql://username:password@host:port/dbname
```

For Supabase with SSL, use:

```
postgresql://username:password@host:port/dbname?sslmode=require
```

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
