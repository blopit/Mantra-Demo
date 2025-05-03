"""
Factory for creating service adapters.

This module provides a factory for creating adapters for different services
like Gmail, Calendar, etc.
"""

from typing import Optional, Dict, Any
import logging

from src.providers.google.gmail import GmailAdapter
from src.providers.google.calendar import CalendarAdapter

logger = logging.getLogger(__name__)

class AdapterFactory:
    """Factory for creating service adapters."""
    
    def __init__(self):
        """Initialize the adapter factory."""
        self._adapters: Dict[str, Any] = {
            "gmail": GmailAdapter,
            "calendar": CalendarAdapter
        }
    
    def create_adapter(self, service_type: str) -> Optional[Any]:
        """Create an adapter for the specified service.
        
        Args:
            service_type: Type of service adapter to create (e.g., 'gmail', 'calendar')
            
        Returns:
            Optional[Any]: Created adapter instance or None if service type not supported
        """
        adapter_class = self._adapters.get(service_type.lower())
        if not adapter_class:
            logger.error(f"Unsupported adapter type: {service_type}")
            return None
            
        try:
            return adapter_class()
        except Exception as e:
            logger.error(f"Error creating adapter for {service_type}: {str(e)}")
            return None
    
    def register_adapter(self, service_type: str, adapter_class: Any) -> None:
        """Register a new adapter type.
        
        Args:
            service_type: Type of service adapter (e.g., 'gmail', 'calendar')
            adapter_class: Class to use for creating adapters of this type
        """
        self._adapters[service_type.lower()] = adapter_class
        logger.info(f"Registered adapter for service: {service_type}") 