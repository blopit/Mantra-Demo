"""
Google Gmail module.

This module provides integration with Gmail API.
"""

from .adapter import GmailAdapter
from .service import GmailService

__all__ = ['GmailAdapter', 'GmailService']
