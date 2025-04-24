"""
Logger utility for consistent logging across the Mantra Demo application.

This module provides a standardized way to create and configure loggers
throughout the application, ensuring consistent log formatting and behavior.

Features:
- Consistent log format across all modules
- Configurable log level based on environment variables
- Stream handler to stdout for easy viewing in console/terminal
- File handlers for error and debug logs with rotation
- Prevents duplicate log handlers when called multiple times
- Performance optimizations for production environments
"""

import os
import logging
import logging.handlers
import sys
from typing import Optional
from pathlib import Path

# Default log format
DEFAULT_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
VERBOSE_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(pathname)s:%(lineno)d - %(message)s'
DEFAULT_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

def setup_logging():
    """
    Configure global logging for the application.

    This function sets up logging with appropriate handlers and formatters
    based on the environment (development, production, testing).

    Returns:
        logging.Logger: Root logger configured for the application
    """
    # Get environment variables for configuration
    debug_mode = os.getenv("DEBUG", "False").lower() == "true"
    log_level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_name, logging.INFO)

    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers to avoid duplicates when reloading
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create formatters
    verbose_formatter = logging.Formatter(
        VERBOSE_FORMAT,
        datefmt=DEFAULT_DATE_FORMAT
    )
    standard_formatter = logging.Formatter(
        DEFAULT_FORMAT,
        datefmt=DEFAULT_DATE_FORMAT
    )

    # Console handler (always enabled)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(standard_formatter)
    console_handler.setLevel(logging.DEBUG if debug_mode else logging.INFO)
    root_logger.addHandler(console_handler)

    # File handler for errors (always enabled)
    error_file_handler = logging.handlers.RotatingFileHandler(
        log_dir / "error.log",
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5
    )
    error_file_handler.setLevel(logging.ERROR)
    error_file_handler.setFormatter(verbose_formatter)
    root_logger.addHandler(error_file_handler)

    # File handler for all logs (only in debug mode or if explicitly enabled)
    if debug_mode or os.getenv("ENABLE_DEBUG_LOG", "False").lower() == "true":
        debug_file_handler = logging.handlers.RotatingFileHandler(
            log_dir / "debug.log",
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5
        )
        debug_file_handler.setLevel(log_level)
        debug_file_handler.setFormatter(verbose_formatter)
        root_logger.addHandler(debug_file_handler)

    # Set SQLAlchemy logging level
    logging.getLogger('sqlalchemy.engine').setLevel(
        logging.INFO if debug_mode else logging.WARNING
    )

    # Set other third-party library logging levels
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)

    # Create and return application logger
    logger = logging.getLogger('mantra_demo')
    logger.info(f"Logging initialized with level {log_level_name}")

    return logger

def get_logger(name: Optional[str] = None, level: Optional[int] = None) -> logging.Logger:
    """
    Get a configured logger instance with consistent formatting.

    This function creates or retrieves a logger with the specified name and
    configures it with a consistent format. If the logger already has handlers,
    it won't add new ones to prevent duplicate log entries.

    Args:
        name: Optional name for the logger. If not provided, uses the module name.
            Using __name__ as the name parameter creates a logger hierarchy that
            matches your module structure.
        level: The logging level to set. If None, uses the level from environment.
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
    # Get environment variables for configuration if level not specified
    if level is None:
        debug_mode = os.getenv("DEBUG", "False").lower() == "true"
        log_level_name = os.getenv("LOG_LEVEL", "INFO").upper()
        level = getattr(logging, log_level_name, logging.INFO)

    # Get or create logger with the specified name
    # If name is None, use the name of the module that called this function
    logger = logging.getLogger(name or __name__)

    # Set the logging level
    logger.setLevel(level)

    # Only add handlers if the logger doesn't already have any and root logger doesn't have handlers
    # This prevents duplicate log entries when the function is called multiple times
    root_logger = logging.getLogger()
    if not logger.handlers and not root_logger.handlers:
        # Create a handler that writes to stdout (console)
        handler = logging.StreamHandler(sys.stdout)

        # Create a formatter with timestamp, logger name, level, and message
        formatter = logging.Formatter(
            DEFAULT_FORMAT,
            datefmt=DEFAULT_DATE_FORMAT
        )

        # Apply the formatter to the handler
        handler.setFormatter(formatter)

        # Add the handler to the logger
        logger.addHandler(handler)

    return logger