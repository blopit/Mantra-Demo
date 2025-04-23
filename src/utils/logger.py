"""
Logger utility for consistent logging across the Mantra Demo application.

This module provides a standardized way to create and configure loggers
throughout the application, ensuring consistent log formatting and behavior.

Features:
- Consistent log format across all modules
- Configurable log level
- Stream handler to stdout for easy viewing in console/terminal
- Prevents duplicate log handlers when called multiple times
"""

import logging
import sys
from typing import Optional

def get_logger(name: Optional[str] = None, level: int = logging.INFO) -> logging.Logger:
    """
    Get a configured logger instance with consistent formatting.

    This function creates or retrieves a logger with the specified name and
    configures it with a consistent format. If the logger already has handlers,
    it won't add new ones to prevent duplicate log entries.

    Args:
        name: Optional name for the logger. If not provided, uses the module name.
            Using __name__ as the name parameter creates a logger hierarchy that
            matches your module structure.
        level: The logging level to set. Defaults to logging.INFO.
            Options include: logging.DEBUG, logging.INFO, logging.WARNING,
            logging.ERROR, logging.CRITICAL

    Returns:
        logging.Logger: Configured logger instance ready for use.

    Example:
        ```python
        from src.utils.logger import get_logger

        # Create a logger for the current module
        logger = get_logger(__name__)

        # Log messages at different levels
        logger.debug("Debug message - only shown when DEBUG level is enabled")
        logger.info("Info message - general information about program execution")
        logger.warning("Warning message - something unexpected but not critical")
        logger.error("Error message - something failed")
        logger.critical("Critical message - serious failure")
        ```
    """
    # Get or create logger with the specified name
    # If name is None, use the name of the module that called this function
    logger = logging.getLogger(name or __name__)

    # Only add handlers if the logger doesn't already have any
    # This prevents duplicate log entries when the function is called multiple times
    if not logger.handlers:
        # Create a handler that writes to stdout (console)
        handler = logging.StreamHandler(sys.stdout)

        # Create a formatter with timestamp, logger name, level, and message
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'  # Custom date format
        )

        # Apply the formatter to the handler
        handler.setFormatter(formatter)

        # Add the handler to the logger
        logger.addHandler(handler)

        # Set the logging level
        logger.setLevel(level)

    return logger