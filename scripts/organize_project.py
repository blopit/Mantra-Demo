#!/usr/bin/env python
"""
Project organization script for Mantra Demo.

This script helps organize the project structure by:
1. Creating necessary directories
2. Moving scripts to the scripts directory
3. Updating imports and references
4. Creating symlinks for backward compatibility

Usage:
    python scripts/organize_project.py [--dry-run]
"""

import os
import sys
import shutil
import argparse
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("organize_project")

def create_directories(dry_run: bool = False) -> None:
    """
    Create necessary directories if they don't exist.
    
    Args:
        dry_run: If True, don't actually create directories
    """
    directories = [
        "scripts",
        "docs",
        "docs/providers",
        "docs/routes",
    ]
    
    for directory in directories:
        if not os.path.exists(directory):
            if dry_run:
                logger.info(f"Would create directory: {directory}")
            else:
                os.makedirs(directory, exist_ok=True)
                logger.info(f"Created directory: {directory}")
        else:
            logger.info(f"Directory already exists: {directory}")

def create_symlinks(dry_run: bool = False) -> None:
    """
    Create symlinks for backward compatibility.
    
    Args:
        dry_run: If True, don't actually create symlinks
    """
    symlinks = [
        ("run_tests.py", "scripts/run_tests.py"),
        ("switch_env.py", "scripts/switch_env.py"),
    ]
    
    for link_name, target in symlinks:
        if os.path.exists(link_name) and not os.path.islink(link_name):
            logger.warning(f"File exists and is not a symlink: {link_name}")
            continue
            
        if os.path.islink(link_name):
            if dry_run:
                logger.info(f"Would update symlink: {link_name} -> {target}")
            else:
                os.unlink(link_name)
                os.symlink(target, link_name)
                logger.info(f"Updated symlink: {link_name} -> {target}")
        else:
            if dry_run:
                logger.info(f"Would create symlink: {link_name} -> {target}")
            else:
                os.symlink(target, link_name)
                logger.info(f"Created symlink: {link_name} -> {target}")

def update_imports(dry_run: bool = False) -> None:
    """
    Update imports in Python files to reflect the new structure.
    
    Args:
        dry_run: If True, don't actually update files
    """
    # Files that might need import updates
    files_to_check = [
        "app.py",
        "src/main.py",
    ]
    
    for file_path in files_to_check:
        if not os.path.exists(file_path):
            logger.warning(f"File not found: {file_path}")
            continue
            
        with open(file_path, 'r') as f:
            content = f.read()
            
        # Update imports
        updated_content = content
        
        # Example: Update run_tests.py import
        if "import run_tests" in content:
            updated_content = updated_content.replace(
                "import run_tests", 
                "import scripts.run_tests as run_tests"
            )
            
        # Example: Update switch_env.py import
        if "import switch_env" in content:
            updated_content = updated_content.replace(
                "import switch_env", 
                "import scripts.switch_env as switch_env"
            )
            
        if content != updated_content:
            if dry_run:
                logger.info(f"Would update imports in: {file_path}")
            else:
                with open(file_path, 'w') as f:
                    f.write(updated_content)
                logger.info(f"Updated imports in: {file_path}")
        else:
            logger.info(f"No import updates needed in: {file_path}")

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Organize project structure",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.split("\n\n")[1]  # Use the usage examples from the docstring
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't actually make changes, just show what would be done"
    )
    
    args = parser.parse_args()
    
    logger.info("Organizing project structure...")
    
    # Create directories
    create_directories(args.dry_run)
    
    # Create symlinks
    create_symlinks(args.dry_run)
    
    # Update imports
    update_imports(args.dry_run)
    
    if args.dry_run:
        logger.info("\nThis was a dry run. No changes were actually made.")
        logger.info("Run without --dry-run to make the changes.")
    else:
        logger.info("\nProject organization complete.")

if __name__ == "__main__":
    main()
