#!/usr/bin/env python
"""
Complete project organization script for Mantra Demo.

This script runs all organization tasks in sequence:
1. Organizes the project structure
2. Consolidates routes
3. Cleans up excess READMEs

Usage:
    python scripts/organize_all.py [--dry-run]
"""

import os
import sys
import argparse
import logging
import subprocess
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("organize_all")

def run_script(script_path: str, dry_run: bool = False) -> None:
    """
    Run a Python script.
    
    Args:
        script_path: Path to the script
        dry_run: If True, add --dry-run flag
    """
    cmd = [sys.executable, script_path]
    
    if dry_run:
        cmd.append("--dry-run")
        
    logger.info(f"Running: {' '.join(cmd)}")
    
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running {script_path}: {e}")
        sys.exit(1)

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Run all organization tasks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.split("\n\n")[1]  # Use the usage examples from the docstring
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't actually make changes, just show what would be done"
    )
    
    args = parser.parse_args()
    
    logger.info("Starting complete project organization...")
    
    # Run organize_project.py
    logger.info("\n=== Organizing Project Structure ===")
    run_script("scripts/organize_project.py", args.dry_run)
    
    # Run consolidate_routes.py
    logger.info("\n=== Consolidating Routes ===")
    run_script("scripts/consolidate_routes.py", args.dry_run)
    
    # Run cleanup_readmes.py
    logger.info("\n=== Cleaning Up READMEs ===")
    run_script("scripts/cleanup_readmes.py", args.dry_run)
    
    logger.info("\nAll organization tasks completed successfully.")
    
    if args.dry_run:
        logger.info("\nThis was a dry run. No changes were actually made.")
        logger.info("Run without --dry-run to make the changes.")

if __name__ == "__main__":
    main()
