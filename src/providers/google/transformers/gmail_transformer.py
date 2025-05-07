"""Gmail node transformer for n8n workflows.

This module transforms n8n Gmail nodes into HTTP Request nodes that use
stored user credentials instead of n8n's built-in Gmail OAuth2 credentials.
"""

from typing import Dict, Any, List
import base64
from email.mime.text import MIMEText
import json
import uuid

class GmailTransformer:
    """Transforms n8n Gmail nodes into HTTP Request nodes"""
    
    GMAIL_API_BASE = "https://gmail.googleapis.com/gmail/v1/users/me"
    
    @staticmethod
    def transform_node(node: Dict[str, Any], workflow: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Transform a Gmail node into one or more HTTP Request nodes
        
        Args:
            node: The n8n Gmail node to transform
            workflow: The complete workflow definition
            
        Returns:
            List[Dict[str, Any]]: List of replacement nodes
        """
        operation = node.get('parameters', {}).get('operation', '')
        node_id = node.get('id', '')
        
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
        
        # Create token refresh node
        token_node = {
            'id': f"{node_id}_token",
            'name': f"{node['name']} - Get Access Token",
            'type': 'n8n-nodes-base.httpRequest',
            'position': [node['position'][0] - 200, node['position'][1]],
            'parameters': {
                'url': 'https://oauth2.googleapis.com/token',
                'method': 'POST',
                'authentication': 'none',
                'allowUnauthorizedCerts': True,
                'options': {},
                'headers': {
                    'parameters': [
                        {
                            'name': 'Content-Type',
                            'value': 'application/x-www-form-urlencoded'
                        }
                    ]
                },
                'bodyParameters': {
                    'parameters': [
                        {
                            'name': 'grant_type',
                            'value': 'refresh_token'
                        },
                        {
                            'name': 'client_id',
                            'value': '={{ $json["client_id"] }}'
                        },
                        {
                            'name': 'client_secret',
                            'value': '={{ $json["client_secret"] }}'
                        },
                        {
                            'name': 'refresh_token',
                            'value': '={{ $json["refresh_token"] }}'
                        }
                    ]
                }
            },
            'continueOnFail': True
        }
        
        # Create main operation node with error handling
        operation_node = {
            'id': node_id,  # Preserve original node ID
            'name': node['name'],  # Keep original name
            'type': 'n8n-nodes-base.httpRequest',
            'position': node['position'],
            'parameters': {
                'authentication': 'none',
                'headers': {
                    'parameters': [
                        {
                            'name': 'Authorization',
                            'value': '=Bearer {{ $node["' + token_node['name'] + '"].json["access_token"] }}'
                        }
                    ]
                },
                'options': {
                    'redirect': {
                        'redirect': True,
                        'followRedirects': True
                    },
                    'timeout': 10000,
                    'retry': {
                        'maxTries': 3,
                        'waitBetweenTries': 5000
                    }
                }
            },
            'continueOnFail': True
        }
        
        # Configure operation-specific parameters
        if operation == 'getAll':
            operation_node['parameters'].update({
                'url': f"{GmailTransformer.GMAIL_API_BASE}/messages",
                'method': 'GET',
                'queryParameters': {
                    'parameters': [
                        {
                            'name': 'maxResults',
                            'value': node['parameters'].get('maxResults', '100')
                        },
                        {
                            'name': 'q',
                            'value': node['parameters'].get('q', '')
                        }
                    ]
                }
            })
            
            return [error_handler, token_node, operation_node]
            
        elif operation == 'send':
            operation_node['parameters'].update({
                'url': f"{GmailTransformer.GMAIL_API_BASE}/messages/send",
                'method': 'POST',
                'headers': {
                    'parameters': [
                        {
                            'name': 'Authorization',
                            'value': '=Bearer {{ $node["' + token_node['name'] + '"].json["access_token"] }}'
                        },
                        {
                            'name': 'Content-Type',
                            'value': 'application/json'
                        }
                    ]
                },
                'body': {
                    'raw': '={{ $json.raw }}'  # Expects base64 encoded email from MIME node
                }
            })
            
            # Create MIME node to construct email
            mime_node = {
                'id': f"{node_id}_mime",
                'name': f"{node['name']} - Create Email",
                'type': 'n8n-nodes-base.function',
                'position': [node['position'][0] - 100, node['position'][1]],
                'parameters': {
                    'functionCode': """
                    // Get email parameters
                    const to = $parameter['sendTo'];
                    const subject = $parameter['subject'];
                    const message = $parameter['message'];
                    const cc = $parameter['options'] ? $parameter['options']['ccList'] : undefined;
                    
                    // Construct email headers
                    let headers = [
                        `To: ${to}`,
                        `Subject: ${subject}`
                    ];
                    
                    if (cc) headers.push(`Cc: ${cc}`);
                    
                    // Construct full email
                    const email = headers.join('\\r\\n') + '\\r\\n\\r\\n' + message;
                    
                    // Base64 encode
                    const encoded = Buffer.from(email).toString('base64');
                    
                    // Return as raw message
                    return [{json: {raw: encoded}}];
                    """
                }
            }
            
            return [error_handler, token_node, mime_node, operation_node]
            
        elif operation == 'get':
            operation_node['parameters'].update({
                'url': f"{GmailTransformer.GMAIL_API_BASE}/messages/{{{{$parameter['messageId']}}}}",
                'method': 'GET',
                'queryParameters': {
                    'parameters': [
                        {
                            'name': 'format',
                            'value': 'full'
                        }
                    ]
                }
            })
            
            return [error_handler, token_node, operation_node]
            
        else:
            raise ValueError(f"Unsupported Gmail operation: {operation}") 