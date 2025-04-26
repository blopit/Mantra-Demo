"""
Transformer for converting n8n workflow nodes to Google-specific implementations.
"""
from typing import Dict, Any, List
import json
import logging

logger = logging.getLogger(__name__)

class GoogleWorkflowTransformer:
    """
    Transforms n8n workflow nodes into Google-specific implementations.
    
    This transformer handles the conversion of n8n nodes that interact with
    Google services (Gmail, Calendar, Drive, etc.) into our internal
    representation.
    """
    
    def __init__(self):
        self.supported_nodes = {
            'gmail': self._transform_gmail_node,
            'googleCalendar': self._transform_calendar_node,
            'googleDrive': self._transform_drive_node,
            'googleSheets': self._transform_sheets_node
        }
    
    def transform_workflow(self, workflow: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform an n8n workflow into our internal representation.
        
        Args:
            workflow (Dict[str, Any]): The n8n workflow definition
            
        Returns:
            Dict[str, Any]: Transformed workflow definition
        """
        try:
            nodes = workflow.get('nodes', [])
            transformed_nodes = []
            
            for node in nodes:
                node_type = node.get('type', '').lower()
                if node_type in self.supported_nodes:
                    transformed_node = self.supported_nodes[node_type](node)
                    transformed_nodes.append(transformed_node)
                else:
                    # Keep unsupported nodes as-is with a warning
                    logger.warning(f"Unsupported node type: {node_type}")
                    transformed_nodes.append(node)
            
            # Log the transformed workflow for testing
            logger.info("Transformed workflow:")
            logger.info(json.dumps(transformed_nodes, indent=2))
            
            return {
                **workflow,
                'nodes': transformed_nodes
            }
            
        except Exception as e:
            logger.error(f"Error transforming workflow: {str(e)}")
            raise
    
    def _transform_gmail_node(self, node: Dict[str, Any]) -> Dict[str, Any]:
        """Transform Gmail node operations."""
        return {
            **node,
            'provider': 'google',
            'service': 'gmail',
            'transformed': True,
            'credentials': {
                'type': 'oauth2',
                'required_scopes': ['https://www.googleapis.com/auth/gmail.modify']
            }
        }
    
    def _transform_calendar_node(self, node: Dict[str, Any]) -> Dict[str, Any]:
        """Transform Google Calendar node operations."""
        return {
            **node,
            'provider': 'google',
            'service': 'calendar',
            'transformed': True,
            'credentials': {
                'type': 'oauth2',
                'required_scopes': ['https://www.googleapis.com/auth/calendar']
            }
        }
    
    def _transform_drive_node(self, node: Dict[str, Any]) -> Dict[str, Any]:
        """Transform Google Drive node operations."""
        return {
            **node,
            'provider': 'google',
            'service': 'drive',
            'transformed': True,
            'credentials': {
                'type': 'oauth2',
                'required_scopes': ['https://www.googleapis.com/auth/drive']
            }
        }
    
    def _transform_sheets_node(self, node: Dict[str, Any]) -> Dict[str, Any]:
        """Transform Google Sheets node operations."""
        return {
            **node,
            'provider': 'google',
            'service': 'sheets',
            'transformed': True,
            'credentials': {
                'type': 'oauth2',
                'required_scopes': ['https://www.googleapis.com/auth/spreadsheets']
            }
        } 