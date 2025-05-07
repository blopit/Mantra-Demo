"""
Transformer for converting n8n workflow nodes to Google-specific implementations.
"""
from typing import Dict, Any, List, Optional
import json
import logging

logger = logging.getLogger(__name__)

class GoogleWorkflowTransformer:
    """
    Transforms n8n workflow nodes into Google-specific implementations.
    
    This transformer handles the conversion of n8n nodes that interact with
    Google services (Gmail, Calendar, Drive, etc.) into our internal
    representation while maintaining N8N compatibility.
    """
    
    def __init__(self):
        self.supported_nodes = {
            'gmail': self._transform_gmail_node,
            'googleCalendar': self._transform_calendar_node,
            'googleDrive': self._transform_drive_node,
            'googleSheets': self._transform_sheets_node
        }
        # Internal mapping of node IDs to Google-specific metadata
        self._node_metadata: Dict[str, Dict[str, Any]] = {}
        
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
            
            # Clear previous metadata
            self._node_metadata = {}
            
            # First pass: identify and transform trigger nodes
            trigger_nodes = [node for node in nodes if self._is_trigger_node(node)]
            non_trigger_nodes = [node for node in nodes if not self._is_trigger_node(node)]
            
            # Transform trigger nodes to "executed by other workflow" triggers
            for node in trigger_nodes:
                transformed_node = self._transform_trigger_node(node)
                transformed_nodes.append(transformed_node)
            
            # Transform remaining nodes
            for node in non_trigger_nodes:
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
            
            # Log the internal metadata mapping
            logger.info("Node metadata mapping:")
            logger.info(json.dumps(self._node_metadata, indent=2))
            
            return {
                **workflow,
                'nodes': transformed_nodes
            }
            
        except Exception as e:
            logger.error(f"Error transforming workflow: {str(e)}")
            raise
    
    def get_node_metadata(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Get Google-specific metadata for a node."""
        return self._node_metadata.get(node_id)
    
    def _is_trigger_node(self, node: Dict[str, Any]) -> bool:
        """Check if a node is a trigger node."""
        node_type = node.get('type', '').lower()
        return 'trigger' in node_type or node_type == 'n8n-nodes-base.webhook'
    
    def _transform_trigger_node(self, node: Dict[str, Any]) -> Dict[str, Any]:
        """Transform any trigger node (including webhooks) to an 'executed by other workflow' trigger."""
        node_id = str(node.get('id', ''))
        node_name = node.get('name', 'Workflow Trigger')
        
        # Store metadata about the original trigger
        self._node_metadata[node_id] = {
            'original_type': node.get('type'),
            'original_parameters': node.get('parameters', {}),
            'transformed_type': 'n8n-nodes-base.executeWorkflow'
        }
        
        # Convert all trigger nodes to executeWorkflow
        return {
            'id': node_id,
            'name': node_name,
            'type': 'n8n-nodes-base.executeWorkflow',
            'parameters': {
                'workflowId': '',  # Will be set by the executing workflow
                'executionMode': 'manually',
                'triggerTimes': '1',
                'arguments': {
                    'name': node_name,
                    'original_type': node.get('type'),
                    'original_parameters': json.dumps(node.get('parameters', {}))
                }
            },
            'typeVersion': 1,
            'position': node.get('position', [0, 0])
        }
    
    def _transform_gmail_node(self, node: Dict[str, Any]) -> Dict[str, Any]:
        """Transform Gmail node operations."""
        node_id = str(node.get('id', ''))
        
        # Store Google-specific metadata
        self._node_metadata[node_id] = {
            'provider': 'google',
            'service': 'gmail',
            'credentials': {
                'type': 'oauth2',
                'required_scopes': ['https://www.googleapis.com/auth/gmail.modify']
            }
        }
        
        # Return N8N-compatible node structure
        return {
            'id': node_id,
            'name': node.get('name', 'Gmail'),
            'type': 'n8n-nodes-base.gmail',
            'parameters': node.get('parameters', {}),
            'typeVersion': 1,
            'position': node.get('position', [0, 0])
        }
    
    def _transform_calendar_node(self, node: Dict[str, Any]) -> Dict[str, Any]:
        """Transform Google Calendar node operations."""
        node_id = str(node.get('id', ''))
        
        # Store Google-specific metadata
        self._node_metadata[node_id] = {
            'provider': 'google',
            'service': 'calendar',
            'credentials': {
                'type': 'oauth2',
                'required_scopes': ['https://www.googleapis.com/auth/calendar']
            }
        }
        
        # Return N8N-compatible node structure
        return {
            'id': node_id,
            'name': node.get('name', 'Google Calendar'),
            'type': 'n8n-nodes-base.googleCalendar',
            'parameters': node.get('parameters', {}),
            'typeVersion': node.get('typeVersion', 1),
            'position': node.get('position', [0, 0])
        }
    
    def _transform_drive_node(self, node: Dict[str, Any]) -> Dict[str, Any]:
        """Transform Google Drive node operations."""
        node_id = str(node.get('id', ''))
        
        # Store Google-specific metadata
        self._node_metadata[node_id] = {
            'provider': 'google',
            'service': 'drive',
            'credentials': {
                'type': 'oauth2',
                'required_scopes': ['https://www.googleapis.com/auth/drive']
            }
        }
        
        # Return N8N-compatible node structure
        return {
            'id': node_id,
            'name': node.get('name', 'Google Drive'),
            'type': 'n8n-nodes-base.googleDrive',
            'parameters': node.get('parameters', {}),
            'typeVersion': 1,
            'position': node.get('position', [0, 0])
        }
    
    def _transform_sheets_node(self, node: Dict[str, Any]) -> Dict[str, Any]:
        """Transform Google Sheets node operations."""
        node_id = str(node.get('id', ''))
        
        # Store Google-specific metadata
        self._node_metadata[node_id] = {
            'provider': 'google',
            'service': 'sheets',
            'credentials': {
                'type': 'oauth2',
                'required_scopes': ['https://www.googleapis.com/auth/spreadsheets']
            }
        }
        
        # Return N8N-compatible node structure
        return {
            'id': node_id,
            'name': node.get('name', 'Google Sheets'),
            'type': 'n8n-nodes-base.googleSheets',
            'parameters': node.get('parameters', {}),
            'typeVersion': 1,
            'position': node.get('position', [0, 0])
        } 