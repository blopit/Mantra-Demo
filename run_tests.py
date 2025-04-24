#!/usr/bin/env python
"""
Test runner script for the Google authentication functionality.
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path


def run_tests(test_path=None, verbose=False, coverage=False):
    """Run tests with pytest."""
    # Build command
    cmd = ["pytest"]
    
    # Add verbosity
    if verbose:
        cmd.append("-v")
    
    # Add coverage
    if coverage:
        cmd.extend(["--cov=src", "--cov-report=term", "--cov-report=html"])
    
    # Add test path
    if test_path:
        cmd.append(test_path)
    else:
        cmd.append("tests/")
    
    # Run command
    print(f"Running: {' '.join(cmd)}")
    return subprocess.call(cmd)


def main():
    """Parse arguments and run tests."""
    parser = argparse.ArgumentParser(description="Run tests for Google authentication.")
    parser.add_argument(
        "test_path", 
        nargs="?", 
        help="Path to specific test file or directory"
    )
    parser.add_argument(
        "-v", "--verbose", 
        action="store_true", 
        help="Enable verbose output"
    )
    parser.add_argument(
        "-c", "--coverage", 
        action="store_true", 
        help="Generate coverage report"
    )
    parser.add_argument(
        "--unit", 
        action="store_true", 
        help="Run only unit tests"
    )
    parser.add_argument(
        "--integration", 
        action="store_true", 
        help="Run only integration tests"
    )
    
    args = parser.parse_args()
    
    # Determine test path
    test_path = args.test_path
    if args.unit:
        test_path = "tests/unit/"
    elif args.integration:
        test_path = "tests/integration/"
    
    # Run tests
    return run_tests(test_path, args.verbose, args.coverage)


if __name__ == "__main__":
    sys.exit(main())
