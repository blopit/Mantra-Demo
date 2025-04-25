#!/usr/bin/env python
"""
Route consolidation script for Mantra Demo.

This script helps consolidate duplicate routes between the 'custom_routes' and 'routes' directories.
It analyzes the routes, identifies duplicates, and helps migrate them to a single location.

Usage:
    python scripts/consolidate_routes.py
"""

import os
import re
import logging
from pathlib import Path
from typing import Dict, List, Set, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("consolidate_routes")

# Paths
SRC_DIR = Path("src")
ROUTES_DIR = SRC_DIR / "routes"
CUSTOM_ROUTES_DIR = SRC_DIR / "custom_routes"

def extract_route_paths(file_path: Path) -> Set[str]:
    """
    Extract route paths from a FastAPI router file.
    
    Args:
        file_path: Path to the router file
        
    Returns:
        Set of route paths
    """
    route_paths = set()
    
    # Regex patterns to match route decorators
    patterns = [
        r'@router\.(?:get|post|put|delete|patch)\s*\(\s*[\'"]([^\'"]+)[\'"]',
        r'@app\.(?:get|post|put|delete|patch)\s*\(\s*[\'"]([^\'"]+)[\'"]',
    ]
    
    try:
        with open(file_path, 'r') as f:
            content = f.read()
            
        for pattern in patterns:
            matches = re.findall(pattern, content)
            route_paths.update(matches)
            
    except Exception as e:
        logger.error(f"Error extracting routes from {file_path}: {e}")
    
    return route_paths

def find_all_routes() -> Dict[str, Dict[str, Set[str]]]:
    """
    Find all routes in both directories.
    
    Returns:
        Dictionary mapping directory names to dictionaries mapping file names to sets of route paths
    """
    routes = {
        "routes": {},
        "custom_routes": {}
    }
    
    # Process routes directory
    for file_path in ROUTES_DIR.glob("**/*.py"):
        if file_path.is_file():
            relative_path = file_path.relative_to(SRC_DIR / "routes")
            routes["routes"][str(relative_path)] = extract_route_paths(file_path)
    
    # Process custom_routes directory
    for file_path in CUSTOM_ROUTES_DIR.glob("**/*.py"):
        if file_path.is_file():
            relative_path = file_path.relative_to(SRC_DIR / "custom_routes")
            routes["custom_routes"][str(relative_path)] = extract_route_paths(file_path)
    
    return routes

def find_duplicate_routes(routes: Dict[str, Dict[str, Set[str]]]) -> Dict[str, List[Tuple[str, str]]]:
    """
    Find duplicate routes between the two directories.
    
    Args:
        routes: Dictionary mapping directory names to dictionaries mapping file names to sets of route paths
        
    Returns:
        Dictionary mapping route paths to lists of (directory, file) tuples
    """
    all_routes = {}
    
    # Collect all routes
    for directory, files in routes.items():
        for file, paths in files.items():
            for path in paths:
                if path not in all_routes:
                    all_routes[path] = []
                all_routes[path].append((directory, file))
    
    # Filter for duplicates
    duplicate_routes = {path: locations for path, locations in all_routes.items() if len(locations) > 1}
    
    return duplicate_routes

def suggest_consolidation(duplicate_routes: Dict[str, List[Tuple[str, str]]]) -> None:
    """
    Suggest consolidation strategy for duplicate routes.
    
    Args:
        duplicate_routes: Dictionary mapping route paths to lists of (directory, file) tuples
    """
    if not duplicate_routes:
        logger.info("No duplicate routes found.")
        return
    
    logger.info(f"Found {len(duplicate_routes)} duplicate routes:")
    
    for path, locations in duplicate_routes.items():
        logger.info(f"\nRoute: {path}")
        logger.info("Defined in:")
        for directory, file in locations:
            logger.info(f"  - {directory}/{file}")
    
    logger.info("\nSuggested consolidation:")
    logger.info("1. Keep routes in src/routes directory")
    logger.info("2. Remove duplicate routes from src/custom_routes")
    logger.info("3. Update imports in app.py")
    
    # Generate migration plan
    logger.info("\nMigration plan:")
    
    # Group by files
    files_to_update = {}
    for path, locations in duplicate_routes.items():
        for directory, file in locations:
            if directory == "custom_routes":
                if file not in files_to_update:
                    files_to_update[file] = []
                files_to_update[file].append(path)
    
    for file, paths in files_to_update.items():
        logger.info(f"\nRemove these routes from src/custom_routes/{file}:")
        for path in paths:
            logger.info(f"  - {path}")

def main():
    """Main entry point for the script."""
    logger.info("Analyzing routes...")
    
    # Find all routes
    routes = find_all_routes()
    
    # Find duplicate routes
    duplicate_routes = find_duplicate_routes(routes)
    
    # Suggest consolidation
    suggest_consolidation(duplicate_routes)
    
    logger.info("\nAnalysis complete.")

if __name__ == "__main__":
    main()
