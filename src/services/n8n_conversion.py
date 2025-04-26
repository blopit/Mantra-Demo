"""
Service for converting n8n workflows to HTTP requests.
This module handles the logic for:
- Parsing n8n workflow JSONs
- Converting n8n nodes to HTTP requests
- Mapping credentials to user accounts
- Generating API schemas
- Executing workflow nodes
"""

import json
import logging
from typing import Dict, List, Any, Optional
from fastapi import Depends, HTTPException, status
import requests
from sqlalchemy.orm import Session

from src.utils.database import get_db
from src.models.users import Users
from src.services.google_integration import GoogleIntegrationService

logger = logging.getLogger(__name__)

class N8nConversionService:
    """Service for converting n8n workflows to HTTP requests"""
    
    def __init__(self, db: Session = Depends(get_db)):
        self.db = db
        self.google_service = GoogleIntegrationService(db)
    
    def parse_workflow(self, workflow_json: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse an n8n workflow JSON and extract nodes and connections
        
        Args:
            workflow_json: The n8n workflow JSON
            
        Returns:
            Dict with nodes and connections
            
        Raises:
            ValueError: If workflow JSON is invalid
        """
        try:
            # Validate workflow structure
            if not isinstance(workflow_json, dict):
                raise ValueError("Invalid workflow: must be a JSON object")
            
            if not workflow_json.get('nodes'):
                raise ValueError("Invalid workflow: missing nodes")
                
            if not isinstance(workflow_json['nodes'], list):
                raise ValueError("Invalid workflow: nodes must be an array")
            
            # Validate each node
            for node in workflow_json['nodes']:
                if not isinstance(node, dict):
                    raise ValueError("Invalid workflow: each node must be an object")
                    
                if not node.get('id'):
                    raise ValueError("Invalid workflow: node missing id")
                    
                if not node.get('type'):
                    raise ValueError("Invalid workflow: node missing type")
            
            # Log workflow details
            logger.info(f"Parsing workflow with {len(workflow_json['nodes'])} nodes")
            logger.info(f"Node types: {[node['type'] for node in workflow_json['nodes']]}")
            
            return {
                'nodes': workflow_json.get('nodes', []),
                'connections': workflow_json.get('connections', {}),
                'meta': workflow_json.get('meta', {})
            }
            
        except Exception as e:
            logger.error(f"Error parsing workflow: {str(e)}")
            raise ValueError(f"Failed to parse workflow: {str(e)}")
    
    def map_credentials(self, node: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """
        Map n8n node credentials to user's stored credentials
        
        Args:
            node: The n8n node with credentials
            user_id: The ID of the user
            
        Returns:
            Dict with mapped credentials
        """
        node_type = node.get('type', '')
        credentials = {}
        
        # Handle credential mapping for different node types
        if 'gmail' in node_type.lower() or 'google' in node_type.lower():
            # Get Google credentials for the user
            google_integration = self.google_service.get_by_user_id(user_id)
            if not google_integration:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Google integration not found. Please connect your Google account."
                )
            
            credentials = {
                'access_token': google_integration.access_token,
                'refresh_token': google_integration.refresh_token,
                'token_uri': "https://oauth2.googleapis.com/token",
                'client_id': google_integration.client_id,
                'client_secret': google_integration.client_secret,
                'scopes': google_integration.scopes
            }
        
        # Add mapping for other credential types as needed
        return credentials
    
    def convert_node_to_http_request(self, node: Dict[str, Any], credentials: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert an n8n node to an HTTP request
        
        Args:
            node: The n8n node
            credentials: The mapped credentials
            
        Returns:
            Dict with HTTP request details
        """
        node_type = node.get('type', '')
        node_name = node.get('name', '')
        parameters = node.get('parameters', {})
        
        # Default request structure
        request = {
            'method': 'GET',
            'url': '',
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': {}
        }
        
        # Convert different node types
        if node_type == 'n8n-nodes-base.gmailTrigger':
            # Gmail trigger conversion
            request = {
                'method': 'GET',
                'url': 'https://www.googleapis.com/gmail/v1/users/me/messages',
                'headers': {
                    'Authorization': f"Bearer {credentials.get('access_token')}",
                    'Content-Type': 'application/json'
                },
                'params': {
                    'q': 'is:unread',
                    'maxResults': 10
                }
            }
        
        elif node_type == '@n8n/n8n-nodes-langchain.lmChatOpenAi':
            # OpenAI node conversion
            openai_api_key = node.get('credentials', {}).get('openAiApi', {}).get('apiKey', '')
            request = {
                'method': 'POST',
                'url': 'https://api.openai.com/v1/chat/completions',
                'headers': {
                    'Authorization': f"Bearer {openai_api_key}",
                    'Content-Type': 'application/json'
                },
                'body': {
                    'model': parameters.get('model', {}).get('value', 'gpt-4o-mini'),
                    'messages': [
                        {'role': 'system', 'content': parameters.get('systemMessage', '')}
                    ]
                }
            }
        
        elif node_type == 'n8n-nodes-base.gmail':
            # Gmail action conversion
            operation = parameters.get('operation', '')
            
            if operation == 'reply':
                request = {
                    'method': 'POST',
                    'url': f"https://www.googleapis.com/gmail/v1/users/me/messages/{{message_id}}/send",
                    'headers': {
                        'Authorization': f"Bearer {credentials.get('access_token')}",
                        'Content-Type': 'application/json'
                    },
                    'body': {
                        'raw': "{{base64_encoded_email}}"
                    }
                }
            elif operation == 'markAsRead':
                request = {
                    'method': 'POST',
                    'url': f"https://www.googleapis.com/gmail/v1/users/me/messages/{{message_id}}/modify",
                    'headers': {
                        'Authorization': f"Bearer {credentials.get('access_token')}",
                        'Content-Type': 'application/json'
                    },
                    'body': {
                        'removeLabelIds': ['UNREAD']
                    }
                }
        
        elif node_type == '@n8n/n8n-nodes-langchain.textClassifier':
            # Text Classifier node conversion
            request = {
                'method': 'POST',
                'url': 'https://api.openai.com/v1/chat/completions',
                'headers': {
                    'Authorization': f"Bearer {credentials.get('openai_api_key')}",
                    'Content-Type': 'application/json'
                },
                'body': {
                    'model': 'gpt-4o-mini',
                    'messages': [
                        {
                            'role': 'system', 
                            'content': f"You are a text classifier that categorizes input into one of the following categories: {parameters.get('categories', {}).get('categories', [])}"
                        },
                        {
                            'role': 'user',
                            'content': parameters.get('inputText', '')
                        }
                    ]
                }
            }
        
        elif node_type == '@n8n/n8n-nodes-langchain.agent':
            # Agent node conversion
            request = {
                'method': 'POST',
                'url': 'https://api.openai.com/v1/chat/completions',
                'headers': {
                    'Authorization': f"Bearer {credentials.get('openai_api_key')}",
                    'Content-Type': 'application/json'
                },
                'body': {
                    'model': 'gpt-4o',
                    'messages': [
                        {
                            'role': 'system',
                            'content': parameters.get('options', {}).get('systemMessage', '')
                        },
                        {
                            'role': 'user',
                            'content': parameters.get('text', '')
                        }
                    ]
                }
            }
        
        elif node_type == 'n8n-nodes-base.googleCalendarTool':
            # Google Calendar Tool conversion
            request = {
                'method': 'GET',
                'url': 'https://www.googleapis.com/calendar/v3/calendars/primary/events',
                'headers': {
                    'Authorization': f"Bearer {credentials.get('access_token')}",
                    'Content-Type': 'application/json'
                },
                'params': {
                    'timeMin': parameters.get('timeMin', ''),
                    'timeMax': parameters.get('timeMax', ''),
                    'maxResults': 100
                }
            }
        
        # Add more node type conversions as needed
        
        return {
            'node_name': node_name,
            'node_type': node_type,
            'request': request
        }
    
    def generate_api_schema(self, workflow_json: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate API schema for the workflow
        
        Args:
            workflow_json: The n8n workflow JSON
            
        Returns:
            Dict with API schema
        """
        parsed = self.parse_workflow(workflow_json)
        nodes = parsed['nodes']
        connections = parsed['connections']
        
        endpoints = []
        
        # Find trigger nodes
        trigger_nodes = [node for node in nodes if 'Trigger' in node.get('type', '')]
        
        for trigger in trigger_nodes:
            trigger_id = trigger.get('id')
            connected_nodes = []
            
            # Find nodes connected to this trigger
            if trigger_id in connections:
                for connection in connections[trigger_id]['main']:
                    for node_connection in connection:
                        connected_node_id = node_connection.get('node')
                        connected_node = next((n for n in nodes if n.get('id') == connected_node_id), None)
                        if connected_node:
                            connected_nodes.append(connected_node)
            
            # Create endpoint for this trigger
            endpoint = {
                'path': f"/api/workflow/{trigger.get('name', 'trigger').replace(' ', '_').lower()}",
                'method': 'POST',
                'trigger': trigger,
                'connected_nodes': connected_nodes
            }
            
            endpoints.append(endpoint)
        
        return {
            'endpoints': endpoints,
            'nodes': nodes,
            'connections': connections
        }
    
    def execute_node(
        self,
        node: Dict[str, Any],
        workflow_data: Dict[str, Any],
        user_id: str,
        input_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute a single node
        
        Args:
            node: The node to execute
            workflow_data: The workflow data
            user_id: The ID of the user
            input_data: Optional input data for the node
            
        Returns:
            The execution results
        """
        parsed = self.parse_workflow(workflow_data)
        nodes = parsed['nodes']
        
        # Find the node to execute
        node = next((n for n in nodes if n.get('id') == node.get('id')), None)
        if not node:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Node with ID {node.get('id')} not found in workflow"
            )
        
        # Map credentials
        credentials = self.map_credentials(node, user_id)
        
        # Convert node to HTTP request
        http_request = self.convert_node_to_http_request(node, credentials)
        
        # Execute the HTTP request using the requests library
        try:
            request_config = http_request['request']
            response = None
            
            if request_config['method'] == 'GET':
                response = requests.get(
                    request_config['url'],
                    headers=request_config.get('headers', {}),
                    params=request_config.get('params', {}),
                    timeout=30
                )
            elif request_config['method'] == 'POST':
                response = requests.post(
                    request_config['url'],
                    headers=request_config.get('headers', {}),
                    json=request_config.get('body', {}),
                    timeout=30
                )
            
            # Parse response
            if response:
                result = {
                    'status_code': response.status_code,
                    'success': response.status_code < 400,
                    'content': response.json() if response.headers.get('content-type') == 'application/json' else response.text
                }
            else:
                result = {
                    'success': False,
                    'message': "Failed to execute request: Unsupported HTTP method"
                }
                
            return {
                'node': node,
                'http_request': http_request,
                'result': result
            }
        except Exception as e:
            logger.error(f"Error executing node {node.get('id')}: {str(e)}")
            return {
                'node': node,
                'http_request': http_request,
                'result': {
                    'success': False,
                    'message': f"Error executing request: {str(e)}"
                }
            } 