"""
Custom exceptions for the application.
"""

class MantraError(Exception):
    """Base exception for mantra-related errors."""
    pass

class MantraNotFoundError(MantraError):
    """Raised when a mantra is not found."""
    pass

class MantraAlreadyInstalledError(MantraError):
    """Raised when attempting to install a mantra that is already installed."""
    pass 