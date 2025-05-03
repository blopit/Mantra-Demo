"""
Test utilities for the Mantra Demo application.

This module provides common utilities for testing, including:
- Test environment setup
- Test data generation
- Test helpers
"""

import os
import json
import uuid
from pathlib import Path
from typing import Dict, Any, Optional

def setup_test_environment():
    """Set up the test environment."""
    # Set testing flag
    os.environ["TESTING"] = "true"

    # Use in-memory SQLite database for tests
    os.environ["DATABASE_URL"] = "sqlite://"

    # Disable migrations for tests
    os.environ["USE_MIGRATIONS"] = "false"

def load_test_fixture(fixture_name: str) -> Dict[str, Any]:
    """
    Load a test fixture from the fixtures directory.
    
    Args:
        fixture_name: Name of the fixture file (without .json extension)
        
    Returns:
        Dict containing the fixture data
    """
    fixture_path = Path(__file__).parent.parent / "fixtures" / f"{fixture_name}.json"
    with open(fixture_path) as f:
        return json.load(f)

def generate_test_id() -> str:
    """Generate a unique test ID."""
    return f"test_{uuid.uuid4().hex[:8]}"
