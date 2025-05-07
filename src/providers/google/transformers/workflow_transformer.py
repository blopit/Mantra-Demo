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
            logger.info("Starting workflow transformation")
            logger.info(f"Input workflow: {json.dumps(workflow, indent=2)}")
            
            nodes = workflow.get('nodes', [])
            logger.info(f"Found {len(nodes)} nodes to transform")
            transformed_nodes = []
            
            # Clear previous metadata
            self._node_metadata = {}
            
            # Keep track of execute nodes to avoid duplicates
            execute_nodes = set()
            
            # Transform all nodes while preserving trigger nodes
            for node in nodes:
                node_type = node.get('type', '').lower()
                node_id = str(node.get('id', ''))
                
                # If it's a trigger node, keep it and add executeWorkflow node
                if self._is_trigger_node(node):
                    # Keep the original trigger node
                    if not node_type.startswith('n8n-nodes-base.'):
                        node['type'] = f"n8n-nodes-base.{node_type}"
                    
                    # For webhook nodes, ensure proper configuration
                    if 'webhook' in node_type:
                        node['parameters'] = {
                            **node.get('parameters', {}),
                            'path': 'onboarding',
                            'responseMode': 'responseNode',
                            'options': {
                                'allowUnauthorizedAccess': True,
                                'responseCode': 200,
                                'responseData': 'allEntries'
                            }
                        }
                    
                    transformed_nodes.append(node)
                    
                    # Add executeWorkflow node if not already added
                    execute_node = self._create_execute_workflow_node(node)
                    execute_node_id = execute_node['id']
                    if execute_node_id not in execute_nodes:
                        execute_nodes.add(execute_node_id)
                        transformed_nodes.append(execute_node)
                        
                        # Update connections to point to executeWorkflow node
                        if 'connections' in workflow:
                            node_name = node.get('name')
                            if node_name in workflow['connections']:
                                workflow['connections'][execute_node['name']] = workflow['connections'][node_name]
                                # Keep the original connection for backward compatibility
                                # del workflow['connections'][node_name]
                # If it's a Google service node, transform it
                elif any(service in node_type for service in self.supported_nodes.keys()):
                    transformer = self.supported_nodes[next(
                        service for service in self.supported_nodes.keys() 
                        if service in node_type
                    )]
                    transformed_node = transformer(node)
                    transformed_nodes.append(transformed_node)
                else:
                    # For non-Google nodes, keep as is but ensure n8n-nodes-base prefix
                    if not node_type.startswith('n8n-nodes-base.'):
                        node['type'] = f"n8n-nodes-base.{node_type}"
                    transformed_nodes.append(node)
                
                logger.info(f"Processed node: {node.get('name')} (type: {node.get('type')})")
            
            # Remove duplicate nodes
            seen_ids = set()
            unique_nodes = []
            for node in transformed_nodes:
                node_id = node.get('id')
                if node_id not in seen_ids:
                    seen_ids.add(node_id)
                    unique_nodes.append(node)
            
            # Update workflow with transformed nodes
            workflow['nodes'] = unique_nodes
            
            # Add trigger parameters if not present
            if 'triggerParameters' not in workflow:
                workflow['triggerParameters'] = {
                    'email': {'type': 'string', 'required': True},
                    'preferredTime': {'type': 'string', 'format': 'date-time', 'required': True},
                    'company': {'type': 'string', 'required': True}
                }
            
            logger.info("Transformation complete")
            logger.info(f"Node metadata mapping: {json.dumps(self._node_metadata, indent=2)}")
            
            return workflow
            
        except Exception as e:
            logger.error(f"Error transforming workflow: {str(e)}")
            raise
    
    def get_node_metadata(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Get Google-specific metadata for a node."""
        return self._node_metadata.get(node_id)
    
    def _is_trigger_node(self, node: Dict[str, Any]) -> bool:
        """Check if a node is a trigger node."""
        node_type = node.get('type', '').lower()
        return ('trigger' in node_type or 
                node_type == 'n8n-nodes-base.webhook' or 
                node_type == 'n8n-nodes-base.scheduletrigger' or
                node_type == 'scheduletrigger')
    
    def _create_execute_workflow_node(self, trigger_node: Dict[str, Any]) -> Dict[str, Any]:
        """Create an executeWorkflow node from a trigger node."""
        node_id = str(trigger_node.get('id', '')) + '_execute'
        node_name = trigger_node.get('name', 'Workflow Trigger') + ' Execute'
        
        # Store metadata about the original trigger
        self._node_metadata[node_id] = {
            'original_type': trigger_node.get('type'),
            'original_parameters': trigger_node.get('parameters', {}),
            'transformed_type': 'n8n-nodes-base.executeWorkflow',
            'webhook_url': 'https://blopit.app.n8n.cloud/webhook/execute'  # Base webhook URL
        }
        
        # Create executeWorkflow node with webhook configuration
        return {
            'id': node_id,
            'name': node_name,
            'type': 'n8n-nodes-base.executeWorkflow',
            'parameters': {
                'workflowId': '',  # This will be set by the executor workflow
                'jsonParameters': True,
                'arguments': {
                    'data': {
                        'email': '${data.email}',
                        'preferredTime': '${data.preferredTime}',
                        'company': '${data.company}'
                    }
                }
            },
            'typeVersion': 1,
            'position': [
                trigger_node.get('position', [0, 0])[0] + 200,  # Place it to the right
                trigger_node.get('position', [0, 0])[1]
            ]
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