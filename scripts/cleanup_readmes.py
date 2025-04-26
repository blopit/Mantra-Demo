#!/usr/bin/env python
"""
README cleanup script for Mantra Demo.

This script helps clean up excess README files in the project.
It identifies READMEs that have been consolidated into the docs directory
and can remove them to keep the project structure clean.

Usage:
    python scripts/cleanup_readmes.py [--dry-run]
"""

import os
import argparse
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("cleanup_readmes")

# Paths to exclude (don't remove these READMEs)
EXCLUDE_PATHS = [
    Path("README.md"),  # Main README
    Path(".pytest_cache/README.md"),  # pytest cache README
    Path(".venv"),  # Anything in .venv
]

def find_readme_files() -> list[Path]:
    """
    Find all README files in the project.
    
    Returns:
        List of paths to README files
    """
    readme_files = []
    
    for path in Path(".").rglob("*README*"):
        # Skip excluded paths
        if any(exclude in path.parents or path == exclude for exclude in EXCLUDE_PATHS):
            continue
            
        if path.is_file():
            readme_files.append(path)
    
    return readme_files

def should_remove(path: Path) -> bool:
    """
    Determine if a README file should be removed.
    
    Args:
        path: Path to the README file
        
    Returns:
        True if the file should be removed, False otherwise
    """
    # Don't remove READMEs in the docs directory
    if "docs" in path.parts:
        return False
        
    # Check if the README is for a module that has been documented in docs
    if "src/providers" in str(path):
        return True
        
    if "src/routes" in str(path):
        return True
        
    if "src/custom_routes" in str(path):
        return True
        
    # For other READMEs, check if they're in alembic
    if "alembic" in str(path) and path.name == "README":
        return False  # Keep alembic README
        
    return True

def remove_readme_files(readme_files: list[Path], dry_run: bool = False) -> None:
    """
    Remove README files that should be removed.
    
    Args:
        readme_files: List of paths to README files
        dry_run: If True, don't actually remove files
    """
    for path in readme_files:
        if should_remove(path):
            if dry_run:
                logger.info(f"Would remove: {path}")
            else:
                try:
                    path.unlink()
                    logger.info(f"Removed: {path}")
                except Exception as e:
                    logger.error(f"Error removing {path}: {e}")
        else:
            logger.info(f"Keeping: {path}")

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Clean up excess README files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.split("\n\n")[1]  # Use the usage examples from the docstring
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't actually remove files, just show what would be removed"
    )
    
    args = parser.parse_args()
    
    logger.info("Finding README files...")
    readme_files = find_readme_files()
    
    if not readme_files:
        logger.info("No README files found to clean up.")
        return
        
    logger.info(f"Found {len(readme_files)} README files.")
    
    remove_readme_files(readme_files, args.dry_run)
    
    if args.dry_run:
        logger.info("\nThis was a dry run. No files were actually removed.")
        logger.info("Run without --dry-run to remove the files.")

if __name__ == "__main__":
    main()
