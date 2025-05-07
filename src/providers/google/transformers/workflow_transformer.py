"""
Transformer for converting n8n workflow nodes to Google-specific implementations.
"""
from typing import Dict, Any, List, Optional
import json
import logging
from .gmail_transformer import GmailTransformer
import uuid

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
        self.workflow_data: Dict[str, Any] = {}

    def _create_default_trigger_node(self, workflow: Dict[str, Any]) -> Dict[str, Any]:
        """Create a default execute workflow trigger node.

        Args:
            workflow: The workflow definition

        Returns:
            Dict[str, Any]: The execute workflow trigger node
        """
        # Create an execute workflow trigger node
        trigger_node = {
            "id": str(uuid.uuid4()),  # Generate unique ID to avoid conflicts
            "name": "When Executed by Another Workflow",
            "type": "n8n-nodes-base.executeWorkflowTrigger",
            "typeVersion": 1.1,
            "position": [440, 380],
            "parameters": {
                "workflowId": "",  # Will be set by the executor workflow
                "options": {}
            }
        }

        # Add trigger parameters if they exist
        if "triggerParameters" in workflow:
            trigger_node["parameters"]["options"]["bodyParameters"] = {
                "parameters": [
                    {
                        "name": param_name,
                        "type": param_info.get("type", "string"),
                        "required": param_info.get("required", False)
                    }
                    for param_name, param_info in workflow["triggerParameters"].items()
                ]
            }

        return trigger_node

    def _create_dummy_webhook_trigger(self) -> Dict[str, Any]:
        """Create a dummy webhook trigger node to satisfy n8n's requirement.

        Returns:
            Dict[str, Any]: The webhook trigger node
        """
        return {
            "id": str(uuid.uuid4()),
            "name": "Webhook Trigger",
            "type": "n8n-nodes-base.webhook",
            "typeVersion": 1,
            "position": [240, 380],
            "webhookId": str(uuid.uuid4()),  # Unique webhook ID
            "parameters": {
                "path": "dummy-trigger",
                "responseMode": "responseNode",
                "options": {}
            }
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
            logger.info("Starting workflow transformation")

            # Store workflow data for node transformers
            self.workflow_data = workflow

            # Create a copy of the workflow to modify
            transformed = workflow.copy()
            transformed['nodes'] = []
            transformed['connections'] = {}

            # Add dummy webhook trigger node (required by n8n)
            webhook_node = self._create_dummy_webhook_trigger()
            transformed['nodes'].append(webhook_node)

            # Track nodes that need to be transformed
            nodes_to_transform = workflow.get('nodes', [])
            logger.info(f"Found {len(nodes_to_transform)} nodes to transform")

            # Process each node
            node_mapping = {}
            for node in nodes_to_transform:
                node_type = node.get('type', '').lower()
                logger.info(f"Processing node: {node.get('name', '')} (type: {node_type})")

                # If it's a Google service node, transform it
                node_type_base = node_type.replace('n8n-nodes-base.', '')  # Remove n8n-nodes-base prefix
                logger.debug(f"Node type base: {node_type_base}")

                if any(service in node_type_base for service in self.supported_nodes.keys()):
                    matching_service = next(
                        (service for service in self.supported_nodes.keys()
                        if service in node_type_base),
                        None
                    )

                    if matching_service:
                        logger.debug(f"Found matching service: {matching_service}")
                        transformer = self.supported_nodes[matching_service]

                        try:
                            transformed_nodes = transformer(node)
                            logger.debug(f"Transformed nodes: {len(transformed_nodes)}")
                            transformed['nodes'].extend(transformed_nodes)

                            # Map the original node name to all transformed node names
                            for transformed_node in transformed_nodes:
                                if transformed_node['name'] == node['name']:
                                    node_mapping[node['name']] = transformed_node['name']
                                    break
                            else:
                                # If no exact match found, use the last transformed node
                                node_mapping[node['name']] = transformed_nodes[-1]['name']
                        except Exception as e:
                            logger.error(f"Error transforming node {node['name']}: {str(e)}")
                            logger.error(f"Node data: {json.dumps(node, indent=2)}")
                            raise
                else:
                    # Keep non-Google nodes as is
                    transformed['nodes'].append(node)
                    node_mapping[node['name']] = node['name']

            # Update connections
            for source_name, targets in workflow.get('connections', {}).items():
                # Get the transformed source node name
                transformed_source = node_mapping.get(source_name)
                if not transformed_source:
                    continue

                # Update connections for each target
                for target_list in targets.get('main', []):
                    for target in target_list:
                        target_name = target['node']
                        transformed_target = node_mapping.get(target_name)
                        if not transformed_target:
                            continue

                        # Add the connection
                        if transformed_source not in transformed['connections']:
                            transformed['connections'][transformed_source] = {'main': [[]]}
                        transformed['connections'][transformed_source]['main'][0].append({
                            'node': transformed_target,
                            'type': 'main',
                            'index': 0
                        })

            # Add required settings
            transformed['settings'] = {
                'saveExecutionProgress': True,
                'saveManualExecutions': True,
                'executionOrder': 'v1'
            }

            logger.info("Transformation complete")
            return transformed

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

    def _transform_gmail_node(self, node: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Transform a Gmail node into HTTP Request nodes.

        Args:
            node: The Gmail node to transform

        Returns:
            List[Dict[str, Any]]: List of transformed nodes
        """
        gmail_transformer = GmailTransformer()
        return gmail_transformer.transform_node(node, self.workflow_data)

    def _transform_calendar_node(self, node: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Transform Google Calendar node operations."""
        try:
            logger.debug(f"Transforming calendar node: {json.dumps(node, indent=2)}")
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

            # Create error handler function node
            error_handler = {
                'id': f"{node_id}_error_handler",
                'name': f"{node['name']} - Error Handler",
                'type': 'n8n-nodes-base.function',
                'position': [node['position'][0] - 300, node['position'][1]],
                'parameters': {
                    'functionCode': """
                    // Check if we got an error response
                    if (items[0].json.error) {
                        const error = items[0].json.error;

                        // Handle token errors
                        if (error === 'invalid_grant' || error === 'invalid_token') {
                            items[0].json = {
                                error: 'Authentication failed. Please reconnect your Google account.',
                                code: 401,
                                retry: false
                            };
                        }
                        // Handle rate limiting
                        else if (error.code === 429) {
                            items[0].json = {
                                error: 'Rate limit exceeded. Please try again later.',
                                code: 429,
                                retry: true
                            };
                        }
                        // Handle other errors
                        else {
                            items[0].json = {
                                error: error.message || 'Unknown error occurred',
                                code: error.code || 500,
                                retry: false
                            };
                        }
                        return items;
                    }

                    // If no error, pass through
                    return items;
                    """
                }
            }
        except Exception as e:
            logger.error(f"Error in calendar node transformation: {str(e)}")
            logger.error(f"Node data: {json.dumps(node, indent=2)}")
            raise

        # Create token refresh node using our credentials system
        token_node = {
            'id': f"{node_id}_token",
            'name': f"{node['name']} - Get Access Token",
            'type': 'n8n-nodes-base.httpRequest',
            'position': [node['position'][0] - 200, node['position'][1]],
            'parameters': {
                'url': '={{ $env.MANTRA_API_URL }}/api/v1/google/auth/token',
                'method': 'GET',
                'authentication': 'none',
                'allowUnauthorizedCerts': True,
                'options': {},
                'headers': {
                    'parameters': [
                        {
                            'name': 'Authorization',
                            'value': '=Bearer {{ $env.MANTRA_API_KEY }}'
                        }
                    ]
                }
            },
            'continueOnFail': True
        }

        # Return N8N-compatible node structure
        operation_node = {
            'id': node_id,
            'name': node.get('name', 'Google Calendar'),
            'type': 'n8n-nodes-base.googleCalendar',
            'parameters': node.get('parameters', {}),
            'typeVersion': 1,
            'position': node.get('position', [0, 0])
        }

        return [error_handler, token_node, operation_node]

    def _transform_drive_node(self, node: Dict[str, Any]) -> List[Dict[str, Any]]:
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

        # Create error handler function node
        error_handler = {
            'id': f"{node_id}_error_handler",
            'name': f"{node['name']} - Error Handler",
            'type': 'n8n-nodes-base.function',
            'position': [node['position'][0] - 300, node['position'][1]],
            'parameters': {
                'functionCode': """
                // Check if we got an error response
                if (items[0].json.error) {
                    const error = items[0].json.error;

                    // Handle token errors
                    if (error === 'invalid_grant' || error === 'invalid_token') {
                        items[0].json = {
                            error: 'Authentication failed. Please reconnect your Google account.',
                            code: 401,
                            retry: false
                        };
                    }
                    // Handle rate limiting
                    else if (error.code === 429) {
                        items[0].json = {
                            error: 'Rate limit exceeded. Please try again later.',
                            code: 429,
                            retry: true
                        };
                    }
                    // Handle other errors
                    else {
                        items[0].json = {
                            error: error.message || 'Unknown error occurred',
                            code: error.code || 500,
                            retry: false
                        };
                    }
                    return items;
                }

                // If no error, pass through
                return items;
                """
            }
        }

        # Create token refresh node using our credentials system
        token_node = {
            'id': f"{node_id}_token",
            'name': f"{node['name']} - Get Access Token",
            'type': 'n8n-nodes-base.httpRequest',
            'position': [node['position'][0] - 200, node['position'][1]],
            'parameters': {
                'url': '={{ $env.MANTRA_API_URL }}/api/v1/google/auth/token',
                'method': 'GET',
                'authentication': 'none',
                'allowUnauthorizedCerts': True,
                'options': {},
                'headers': {
                    'parameters': [
                        {
                            'name': 'Authorization',
                            'value': '=Bearer {{ $env.MANTRA_API_KEY }}'
                        }
                    ]
                }
            },
            'continueOnFail': True
        }

        # Return N8N-compatible node structure
        operation_node = {
            'id': node_id,
            'name': node.get('name', 'Google Drive'),
            'type': 'n8n-nodes-base.googleDrive',
            'parameters': node.get('parameters', {}),
            'typeVersion': 1,
            'position': node.get('position', [0, 0])
        }

        return [error_handler, token_node, operation_node]

    def _transform_sheets_node(self, node: Dict[str, Any]) -> List[Dict[str, Any]]:
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

        # Create error handler function node
        error_handler = {
            'id': f"{node_id}_error_handler",
            'name': f"{node['name']} - Error Handler",
            'type': 'n8n-nodes-base.function',
            'position': [node['position'][0] - 300, node['position'][1]],
            'parameters': {
                'functionCode': """
                // Check if we got an error response
                if (items[0].json.error) {
                    const error = items[0].json.error;

                    // Handle token errors
                    if (error === 'invalid_grant' || error === 'invalid_token') {
                        items[0].json = {
                            error: 'Authentication failed. Please reconnect your Google account.',
                            code: 401,
                            retry: false
                        };
                    }
                    // Handle rate limiting
                    else if (error.code === 429) {
                        items[0].json = {
                            error: 'Rate limit exceeded. Please try again later.',
                            code: 429,
                            retry: true
                        };
                    }
                    // Handle other errors
                    else {
                        items[0].json = {
                            error: error.message || 'Unknown error occurred',
                            code: error.code || 500,
                            retry: false
                        };
                    }
                    return items;
                }

                // If no error, pass through
                return items;
                """
            }
        }

        # Create token refresh node using our credentials system
        token_node = {
            'id': f"{node_id}_token",
            'name': f"{node['name']} - Get Access Token",
            'type': 'n8n-nodes-base.httpRequest',
            'position': [node['position'][0] - 200, node['position'][1]],
            'parameters': {
                'url': '={{ $env.MANTRA_API_URL }}/api/v1/google/auth/token',
                'method': 'GET',
                'authentication': 'none',
                'allowUnauthorizedCerts': True,
                'options': {},
                'headers': {
                    'parameters': [
                        {
                            'name': 'Authorization',
                            'value': '=Bearer {{ $env.MANTRA_API_KEY }}'
                        }
                    ]
                }
            },
            'continueOnFail': True
        }

        # Return N8N-compatible node structure
        operation_node = {
            'id': node_id,
            'name': node.get('name', 'Google Sheets'),
            'type': 'n8n-nodes-base.googleSheets',
            'parameters': node.get('parameters', {}),
            'typeVersion': 1,
            'position': node.get('position', [0, 0])
        }

        return [error_handler, token_node, operation_node]