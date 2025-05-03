#!/usr/bin/env python
"""
Database Migration Script for Mantra Demo.

This script consolidates data from multiple SQLite databases into a single database.
It copies tables from source databases to the target database, handling conflicts
and ensuring data integrity.

Usage:
    python scripts/migrate_databases.py

Environment Variables:
    TARGET_DB_PATH: Path to the target database (default: mantra.db)
    LEGACY_DB_PATHS: Comma-separated list of legacy database paths to migrate from
"""

import os
import sys
import sqlite3
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("db_migration")

# Default paths
DEFAULT_TARGET_DB = "mantra.db"
DEFAULT_LEGACY_DBS = "test.db,sqlite.db,mantra_dev.db,agent_memory.db"


def get_database_paths() -> Tuple[str, List[str]]:
    """
    Get database paths from environment variables or use defaults.
    
    Returns:
        Tuple[str, List[str]]: Target database path and list of legacy database paths
    """
    target_db = os.getenv("TARGET_DB_PATH", DEFAULT_TARGET_DB)
    legacy_dbs_str = os.getenv("LEGACY_DB_PATHS", DEFAULT_LEGACY_DBS)
    legacy_dbs = [db.strip() for db in legacy_dbs_str.split(",") if db.strip()]
    
    # Filter out non-existent databases and the target database
    legacy_dbs = [db for db in legacy_dbs if Path(db).exists() and db != target_db]
    
    return target_db, legacy_dbs


def get_tables(conn: sqlite3.Connection) -> List[str]:
    """
    Get all table names from a database.
    
    Args:
        conn: SQLite connection
        
    Returns:
        List[str]: List of table names
    """
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = [row[0] for row in cursor.fetchall()]
    cursor.close()
    return tables


def get_table_schema(conn: sqlite3.Connection, table_name: str) -> str:
    """
    Get the schema (CREATE TABLE statement) for a table.
    
    Args:
        conn: SQLite connection
        table_name: Name of the table
        
    Returns:
        str: CREATE TABLE statement
    """
    cursor = conn.cursor()
    cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    schema = cursor.fetchone()[0]
    cursor.close()
    return schema


def get_table_data(conn: sqlite3.Connection, table_name: str) -> Tuple[List[str], List[Tuple]]:
    """
    Get column names and data from a table.
    
    Args:
        conn: SQLite connection
        table_name: Name of the table
        
    Returns:
        Tuple[List[str], List[Tuple]]: Column names and rows of data
    """
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    
    cursor.execute(f"SELECT * FROM {table_name}")
    rows = cursor.fetchall()
    
    cursor.close()
    return columns, rows


def create_table_if_not_exists(conn: sqlite3.Connection, table_name: str, schema: str) -> None:
    """
    Create a table if it doesn't exist.
    
    Args:
        conn: SQLite connection
        table_name: Name of the table
        schema: CREATE TABLE statement
    """
    cursor = conn.cursor()
    try:
        # Check if table exists
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
        if not cursor.fetchone():
            # Create table
            cursor.execute(schema)
            conn.commit()
            logger.info(f"Created table {table_name}")
        else:
            logger.info(f"Table {table_name} already exists")
    except sqlite3.Error as e:
        logger.error(f"Error creating table {table_name}: {e}")
    finally:
        cursor.close()


def insert_data(conn: sqlite3.Connection, table_name: str, columns: List[str], rows: List[Tuple]) -> int:
    """
    Insert data into a table.
    
    Args:
        conn: SQLite connection
        table_name: Name of the table
        columns: Column names
        rows: Rows of data
        
    Returns:
        int: Number of rows inserted
    """
    if not rows:
        return 0
        
    cursor = conn.cursor()
    inserted = 0
    
    try:
        # Prepare placeholders for the SQL query
        placeholders = ", ".join(["?" for _ in columns])
        columns_str = ", ".join(columns)
        
        # Insert data
        for row in rows:
            try:
                cursor.execute(
                    f"INSERT OR IGNORE INTO {table_name} ({columns_str}) VALUES ({placeholders})",
                    row
                )
                if cursor.rowcount > 0:
                    inserted += 1
            except sqlite3.Error as e:
                logger.warning(f"Error inserting row into {table_name}: {e}")
                continue
                
        conn.commit()
    except sqlite3.Error as e:
        logger.error(f"Error inserting data into {table_name}: {e}")
        conn.rollback()
    finally:
        cursor.close()
        
    return inserted


def migrate_database(source_db: str, target_db: str) -> Dict[str, int]:
    """
    Migrate data from source database to target database.
    
    Args:
        source_db: Path to source database
        target_db: Path to target database
        
    Returns:
        Dict[str, int]: Dictionary mapping table names to number of rows migrated
    """
    if not Path(source_db).exists():
        logger.warning(f"Source database {source_db} does not exist")
        return {}
        
    logger.info(f"Migrating from {source_db} to {target_db}")
    
    # Connect to source database
    try:
        source_conn = sqlite3.connect(source_db)
        source_conn.row_factory = sqlite3.Row
    except sqlite3.Error as e:
        logger.error(f"Error connecting to source database {source_db}: {e}")
        return {}
        
    # Connect to target database
    try:
        target_conn = sqlite3.connect(target_db)
    except sqlite3.Error as e:
        logger.error(f"Error connecting to target database {target_db}: {e}")
        source_conn.close()
        return {}
    
    # Get tables from source database
    tables = get_tables(source_conn)
    logger.info(f"Found {len(tables)} tables in {source_db}: {', '.join(tables)}")
    
    # Migrate each table
    migration_stats = {}
    for table in tables:
        try:
            # Get schema and data
            schema = get_table_schema(source_conn, table)
            columns, rows = get_table_data(source_conn, table)
            
            # Create table in target database if it doesn't exist
            create_table_if_not_exists(target_conn, table, schema)
            
            # Insert data
            inserted = insert_data(target_conn, table, columns, rows)
            migration_stats[table] = inserted
            
            logger.info(f"Migrated {inserted}/{len(rows)} rows from {table}")
        except Exception as e:
            logger.error(f"Error migrating table {table}: {e}")
            continue
    
    # Close connections
    source_conn.close()
    target_conn.close()
    
    return migration_stats


def main():
    """Main function to run the database migration."""
    logger.info("Starting database migration")
    
    # Get database paths
    target_db, legacy_dbs = get_database_paths()
    
    if not legacy_dbs:
        logger.info("No legacy databases found to migrate")
        return
        
    logger.info(f"Target database: {target_db}")
    logger.info(f"Legacy databases: {', '.join(legacy_dbs)}")
    
    # Create target database directory if it doesn't exist
    target_path = Path(target_db)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Migrate each legacy database
    total_stats = {}
    for db in legacy_dbs:
        stats = migrate_database(db, target_db)
        
        # Update total stats
        for table, count in stats.items():
            if table not in total_stats:
                total_stats[table] = 0
            total_stats[table] += count
    
    # Print summary
    logger.info("Migration complete")
    logger.info("Summary:")
    for table, count in total_stats.items():
        logger.info(f"  {table}: {count} rows migrated")


if __name__ == "__main__":
    main()
