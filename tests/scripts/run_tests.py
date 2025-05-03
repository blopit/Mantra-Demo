#!/usr/bin/env python
"""
Enhanced test runner script for the Mantra Demo application.

This script provides a flexible command-line interface for running tests
with various options, including:
- Running specific test files or directories
- Running unit, integration, or e2e tests
- Generating coverage reports
- Setting verbosity levels
- Configuring test database

Usage examples:
    python tests/scripts/run_tests.py                     # Run all tests
    python tests/scripts/run_tests.py --unit              # Run only unit tests
    python tests/scripts/run_tests.py --integration       # Run only integration tests
    python tests/scripts/run_tests.py --e2e               # Run only end-to-end tests
    python tests/scripts/run_tests.py tests/unit/test_*.py # Run specific test files
    python tests/scripts/run_tests.py -v -c               # Run with verbose output and coverage
"""

import os
import sys
import argparse
import subprocess
import logging
from pathlib import Path
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test_runner")

# Load environment variables
load_dotenv()

def setup_test_environment():
    """Set up the test environment."""
    # Set testing flag
    os.environ["TESTING"] = "true"

    # Use in-memory SQLite database for tests
    os.environ["DATABASE_URL"] = "sqlite://"

    # Disable migrations for tests
    os.environ["USE_MIGRATIONS"] = "false"

    logger.info("Test environment configured")

def run_tests(test_path=None, verbose=False, coverage=False, xvs=False, markers=None):
    """
    Run tests with pytest.

    Args:
        test_path (str, optional): Path to specific test file or directory
        verbose (bool): Whether to enable verbose output
        coverage (bool): Whether to generate coverage report
        xvs (bool): Whether to show extra verbose output
        markers (str, optional): Pytest markers to filter tests

    Returns:
        int: Exit code from pytest
    """
    # Set up test environment
    setup_test_environment()

    # Build command
    cmd = ["pytest"]

    # Add verbosity
    if xvs:
        cmd.append("-vvs")
    elif verbose:
        cmd.append("-v")

    # Add coverage
    if coverage:
        cmd.extend([
            "--cov=src",
            "--cov-report=term",
            "--cov-report=html",
            "--cov-report=xml"
        ])

    # Add markers
    if markers:
        cmd.append(f"-m {markers}")

    # Add test path
    if test_path:
        cmd.append(test_path)
    else:
        cmd.append("tests/")

    # Run command
    cmd_str = " ".join(cmd)
    logger.info(f"Running: {cmd_str}")
    return subprocess.call(cmd)

def main():
    """Parse arguments and run tests."""
    parser = argparse.ArgumentParser(
        description="Run tests for Mantra Demo application.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.split("\n\n")[1]  # Use the usage examples from the docstring
    )

    # Test selection arguments
    parser.add_argument(
        "test_path",
        nargs="?",
        help="Path to specific test file or directory"
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
    parser.add_argument(
        "--e2e",
        action="store_true",
        help="Run only end-to-end tests"
    )
    parser.add_argument(
        "-m", "--markers",
        help="Only run tests with the specified pytest markers"
    )

    # Output control arguments
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    parser.add_argument(
        "--xvs",
        action="store_true",
        help="Enable extra verbose output with test output capture"
    )
    parser.add_argument(
        "-c", "--coverage",
        action="store_true",
        help="Generate coverage report"
    )

    args = parser.parse_args()

    # Determine test path
    test_path = args.test_path
    if args.unit:
        test_path = "tests/unit/"
    elif args.integration:
        test_path = "tests/integration/"
    elif args.e2e:
        test_path = "tests/e2e/"

    # Run tests
    return run_tests(
        test_path=test_path,
        verbose=args.verbose,
        coverage=args.coverage,
        xvs=args.xvs,
        markers=args.markers
    )

if __name__ == "__main__":
    sys.exit(main())
