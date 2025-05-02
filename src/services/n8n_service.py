"""
Service for managing n8n workflows.
This module handles the interaction with n8n API for:
- Creating workflows
- Activating/deactivating workflows
- Executing workflow nodes
- Managing workflow lifecycle
"""

import logging
from typing import Dict, Any, Optional, Union
import httpx
from fastapi import HTTPException
import aiohttp
import json
import os
from jsonschema import validate, ValidationError
import asyncio
from fastapi import status

logger = logging.getLogger(__name__)

# JSON Schema for n8n workflow validation
WORKFLOW_SCHEMA = {
    "type": "object",
    "required": ["nodes", "connections"],
    "properties": {
        "name": {"type": "string"},
        "nodes": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": ["id", "type", "parameters"],
                "properties": {
                    "id": {"type": ["string", "integer"]},
                    "type": {"type": "string"},
                    "name": {"type": "string"},
                    "parameters": {"type": "object"},
                    "position": {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 2,
                        "maxItems": 2
                    }
                }
            }
        },
        "connections": {
            "type": "object",
            "patternProperties": {
                "^.*$": {
                    "type": "object",
                    "properties": {
                        "main": {
                            "type": "array",
                            "items": {
                                "type": "array",
                                "items": {
                                    "oneOf": [
                                        {
                                            "type": "object",
                                            "required": ["node", "type", "index"],
                                            "properties": {
                                                "node": {"type": "string"},
                                                "type": {"type": "string"},
                                                "index": {"type": "integer"}
                                            }
                                        },
                                        {"type": "integer"},
                                        {"type": "string"}
                                    ]
                                }
                            }
                        }
                    }
                }
            }
        },
        "settings": {"type": "object"},
        "active": {"type": "boolean"},
        "staticData": {"type": ["object", "null"]},
        "pinData": {"type": "object"},
        "tags": {"type": "array", "items": {"type": "string"}},
        "versionId": {"type": ["integer", "null"]}
    }
}

class N8nService:
    """Service for managing n8n workflows."""
    
    def __init__(self, api_url: str, api_key: str):
        """Initialize the service.
        
        Args:
            api_url: The base URL of the n8n API
            api_key: The API key for authentication
        """
        self.api_url = api_url.rstrip('/')
        self.api_key = api_key
        self.headers = {
            'X-N8N-API-KEY': api_key,
            'Content-Type': 'application/json'
        }
        self.timeout = float(os.getenv("N8N_API_TIMEOUT", "30.0"))
        self.max_retries = int(os.getenv("N8N_MAX_RETRIES", "3"))
        self.retry_delay = float(os.getenv("N8N_RETRY_DELAY", "1.0"))
    
    def parse_workflow(self, workflow_json: Dict[str, Any]) -> Dict[str, Any]:
        """Parse and validate a workflow JSON.
        
        Args:
            workflow_json: The workflow JSON to parse and validate
            
        Returns:
            The validated and prepared workflow
            
        Raises:
            ValueError: If the workflow is invalid or missing required fields
        """
        # Check for required fields
        if 'nodes' not in workflow_json:
            raise ValueError("Workflow JSON missing required fields: nodes")
        if 'connections' not in workflow_json:
            raise ValueError("Workflow JSON missing required fields: connections")
        
        # Define Google service node types that don't need the n8n-nodes-base prefix
        google_service_types = ['gmail', 'googlecalendar', 'googledrive', 'googlesheets']
        
        # Validate node structure
        for i, node in enumerate(workflow_json.get('nodes', [])):
            missing_fields = []
            if 'id' not in node:
                missing_fields.append('id')
            if 'type' not in node:
                missing_fields.append('type')
            if 'name' not in node:
                missing_fields.append('name')
            if 'parameters' not in node:
                missing_fields.append('parameters')
            
            if missing_fields:
                raise ValueError(f"Node {i} missing required fields: {', '.join(missing_fields)}")
            
            # Ensure node type follows n8n format if not already and is not a Google service type
            node_type_lower = node['type'].lower()
            if (not node['type'].startswith('n8n-nodes-base.') and 
                node_type_lower not in google_service_types):
                node['type'] = f"n8n-nodes-base.{node['type']}"
                logger.info(f"Added n8n-nodes-base prefix to node type: {node['type']}")
        
        # Prepare workflow with defaults
        prepared_workflow = self._prepare_workflow_for_n8n(workflow_json)
        
        logger.info(f"Successfully parsed workflow with {len(workflow_json.get('nodes', []))} nodes")
        
        return prepared_workflow
    
    def _validate_workflow_structure(self, workflow_json: Dict[str, Any]) -> None:
        """Validate the workflow structure using JSON Schema.
        
        Args:
            workflow_json: The workflow to validate
            
        Raises:
            ValueError: If the workflow structure is invalid
        """
        try:
            # Validate against JSON Schema
            validate(instance=workflow_json, schema=WORKFLOW_SCHEMA)
            
            # Additional validation for node types
            for node in workflow_json['nodes']:
                # Allow Google service node types that will be handled by GoogleWorkflowTransformer
                google_service_types = ['gmail', 'googlecalendar', 'googledrive', 'googlesheets']
                node_type = node['type'].lower()
                
                if not node['type'].startswith('n8n-nodes-base.') and node_type not in google_service_types:
                    raise ValueError(f"Invalid node type: {node['type']}. Must start with 'n8n-nodes-base.'")
                
                # Log node validation
                logger.debug(f"Validated node: {json.dumps(node, indent=2)}")
            
            # Additional validation for connections
            if 'connections' in workflow_json and isinstance(workflow_json['connections'], dict):
                for node_id, connection in workflow_json['connections'].items():
                    if 'main' in connection and isinstance(connection['main'], list):
                        # Format connections if needed
                        for i, conn_list in enumerate(connection['main']):
                            if isinstance(conn_list, list):
                                for j, conn in enumerate(conn_list):
                                    # Convert integer/string connection to object format if needed
                                    if isinstance(conn, (int, str)):
                                        # Create a properly formatted connection object
                                        logger.info(f"Converting simple connection value {conn} to object format")
                                        workflow_json['connections'][node_id]['main'][i][j] = {
                                            "node": str(conn) if isinstance(conn, int) else conn,
                                            "type": "main",
                                            "index": 0
                                        }
                
            logger.info(f"Successfully validated workflow with {len(workflow_json['nodes'])} nodes")
            
        except ValidationError as e:
            error_msg = f"Workflow validation failed: {str(e)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        except Exception as e:
            error_msg = f"Error validating workflow: {str(e)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
    
    def _prepare_workflow_for_n8n(self, workflow_json: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare a workflow for n8n by adding required fields.
        
        Args:
            workflow_json: The workflow to prepare
            
        Returns:
            The prepared workflow
        """
        # Deep copy to avoid modifying the original
        workflow = json.loads(json.dumps(workflow_json))
        
        # Add required n8n fields with defaults
        workflow.setdefault('name', 'Imported Workflow')
        workflow.setdefault('active', False)
        workflow.setdefault('settings', {})
        workflow.setdefault('staticData', None)
        workflow.setdefault('pinData', {})
        workflow.setdefault('tags', [])
        workflow.setdefault('versionId', 1)
        
        # Add default settings if not present
        workflow['settings'].setdefault('saveExecutionProgress', True)
        workflow['settings'].setdefault('saveManualExecutions', True)
        workflow['settings'].setdefault('callerPolicy', 'workflowsFromSameOwner')
        
        return workflow
    
    async def create_workflow(self, workflow_json: Dict[str, Any]) -> Union[Dict[str, Any], int]:
        """Create a new workflow in n8n.
        
        Args:
            workflow_json: The workflow definition
            
        Returns:
            The ID of the created workflow or workflow details
            
        Raises:
            HTTPException: If workflow creation fails
        """
        try:
            # Validate workflow structure
            try:
                self._validate_workflow_structure(workflow_json)
            except ValueError as validation_error:
                # Provide more detailed error for validation issues
                logger.error(f"Workflow validation error: {str(validation_error)}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid workflow format: {str(validation_error)}"
                )
            
            # Prepare workflow for n8n
            prepared_workflow = self._prepare_workflow_for_n8n(workflow_json)
            
            # Log request details
            logger.info("Creating n8n workflow")
            logger.debug(f"Request URL: {self.api_url}/workflows")
            logger.debug(f"Request headers: {json.dumps(self.headers, indent=2)}")
            logger.debug(f"Request payload: {json.dumps(prepared_workflow, indent=2)}")
            
            retry_count = 0
            while retry_count < self.max_retries:
                try:
                    async with httpx.AsyncClient() as client:
                        response = await client.post(
                            f"{self.api_url}/workflows",
                            headers=self.headers,
                            json=prepared_workflow,
                            timeout=self.timeout
                        )
                        
                        # Log response details
                        logger.debug(f"Response status: {response.status_code}")
                        logger.debug(f"Response headers: {json.dumps(dict(response.headers), indent=2)}")
                        
                        if response.status_code == 400:
                            error_detail = None
                            try:
                                error_json = response.json()
                                if isinstance(error_json, dict):
                                    error_detail = error_json.get('message', error_json)
                                logger.error(f"N8N API error response: {json.dumps(error_json, indent=2)}")
                            except:
                                error_detail = response.text
                                logger.error(f"N8N API error response (text): {error_detail}")
                            
                            raise HTTPException(
                                status_code=400,
                                detail=f"Invalid workflow format: {error_detail}"
                            )
                        
                        response.raise_for_status()
                        result = response.json()
                        
                        if not isinstance(result, dict) or 'id' not in result:
                            raise ValueError("Invalid response from n8n API: missing workflow ID")
                        
                        logger.info(f"Successfully created n8n workflow with ID: {result['id']}")
                        logger.debug(f"Workflow creation response: {json.dumps(result, indent=2)}")
                        return result
                        
                except httpx.HTTPError as e:
                    if retry_count + 1 < self.max_retries:
                        retry_count += 1
                        logger.warning(f"Retrying workflow creation after error (attempt {retry_count}): {str(e)}")
                        await asyncio.sleep(self.retry_delay)
                    else:
                        raise
                        
        except httpx.HTTPError as e:
            logger.error(f"HTTP error creating n8n workflow: {str(e)}")
            if isinstance(e, httpx.HTTPStatusError):
                status_code = e.response.status_code
                error_detail = None
                try:
                    error_json = e.response.json()
                    if isinstance(error_json, dict):
                        error_detail = error_json.get('message', error_json)
                    logger.error(f"N8N API error response: {json.dumps(error_json, indent=2)}")
                except:
                    error_detail = e.response.text
                    logger.error(f"N8N API error response (text): {error_detail}")
                
                raise HTTPException(
                    status_code=status_code,
                    detail=f"Failed to create n8n workflow: {error_detail}"
                )
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create n8n workflow: {str(e)}"
            )
        except ValueError as e:
            logger.error(f"Validation error in workflow JSON: {str(e)}")
            raise HTTPException(
                status_code=400,
                detail=str(e)
            )
        except Exception as e:
            logger.error(f"Unexpected error creating n8n workflow: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create n8n workflow: {str(e)}"
            )
    
    async def activate_workflow(self, workflow_id: int) -> None:
        """Activate a workflow in n8n.
        
        Args:
            workflow_id: The ID of the workflow to activate
            
        Raises:
            HTTPException: If workflow activation fails
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_url}/workflows/{workflow_id}/activate",
                    headers=self.headers,
                    timeout=self.timeout
                )
                
                if response.status_code == 400:
                    error_detail = None
                    try:
                        error_json = response.json()
                        if isinstance(error_json, dict):
                            error_detail = error_json.get('message', error_json)
                    except:
                        error_detail = response.text
                    
                    logger.error(f"N8N API returned 400 error: {error_detail}")
                    raise HTTPException(
                        status_code=400,
                        detail=f"Failed to activate workflow: {error_detail}"
                    )
                
                response.raise_for_status()
                logger.info(f"Successfully activated workflow {workflow_id}")
        except httpx.HTTPError as e:
            logger.error(f"Error activating n8n workflow {workflow_id}: {e}")
            if isinstance(e, httpx.HTTPStatusError):
                status_code = e.response.status_code
                error_detail = None
                try:
                    error_json = e.response.json()
                    if isinstance(error_json, dict):
                        error_detail = error_json.get('message', error_json)
                except:
                    error_detail = e.response.text
                
                raise HTTPException(
                    status_code=status_code,
                    detail=f"Failed to activate workflow: {error_detail}"
                )
            raise HTTPException(
                status_code=500,
                detail=f"Failed to activate workflow: {str(e)}"
            )
    
    async def deactivate_workflow(self, workflow_id: int) -> None:
        """Deactivate a workflow in n8n.
        
        Args:
            workflow_id: The ID of the workflow to deactivate
            
        Raises:
            HTTPException: If workflow deactivation fails
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_url}/workflows/{workflow_id}/deactivate",
                    headers=self.headers,
                    timeout=self.timeout
                )
                
                if response.status_code == 400:
                    error_detail = None
                    try:
                        error_json = response.json()
                        if isinstance(error_json, dict):
                            error_detail = error_json.get('message', error_json)
                    except:
                        error_detail = response.text
                    
                    logger.error(f"N8N API returned 400 error: {error_detail}")
                    raise HTTPException(
                        status_code=400,
                        detail=f"Failed to deactivate workflow: {error_detail}"
                    )
                
                response.raise_for_status()
                logger.info(f"Successfully deactivated workflow {workflow_id}")
        except httpx.HTTPError as e:
            logger.error(f"Error deactivating n8n workflow {workflow_id}: {e}")
            if isinstance(e, httpx.HTTPStatusError):
                status_code = e.response.status_code
                error_detail = None
                try:
                    error_json = e.response.json()
                    if isinstance(error_json, dict):
                        error_detail = error_json.get('message', error_json)
                except:
                    error_detail = e.response.text
                
                raise HTTPException(
                    status_code=status_code,
                    detail=f"Failed to deactivate workflow: {error_detail}"
                )
            raise HTTPException(
                status_code=500,
                detail=f"Failed to deactivate workflow: {str(e)}"
            )
    
    async def delete_workflow(self, workflow_id: int) -> None:
        """Delete a workflow from n8n.
        
        Args:
            workflow_id: The ID of the workflow to delete
            
        Raises:
            HTTPException: If workflow deletion fails
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    f"{self.api_url}/workflows/{workflow_id}",
                    headers=self.headers,
                    timeout=self.timeout
                )
                
                if response.status_code == 400:
                    error_detail = None
                    try:
                        error_json = response.json()
                        if isinstance(error_json, dict):
                            error_detail = error_json.get('message', error_json)
                    except:
                        error_detail = response.text
                    
                    logger.error(f"N8N API returned 400 error: {error_detail}")
                    raise HTTPException(
                        status_code=400,
                        detail=f"Failed to delete workflow: {error_detail}"
                    )
                
                response.raise_for_status()
                logger.info(f"Successfully deleted workflow {workflow_id}")
        except httpx.HTTPError as e:
            logger.error(f"Error deleting n8n workflow {workflow_id}: {e}")
            if isinstance(e, httpx.HTTPStatusError):
                status_code = e.response.status_code
                error_detail = None
                try:
                    error_json = e.response.json()
                    if isinstance(error_json, dict):
                        error_detail = error_json.get('message', error_json)
                except:
                    error_detail = e.response.text
                
                raise HTTPException(
                    status_code=status_code,
                    detail=f"Failed to delete workflow: {error_detail}"
                )
            raise HTTPException(
                status_code=500,
                detail=f"Failed to delete workflow: {str(e)}"
            )
    
    async def execute_workflow(self, workflow_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a workflow with the given data.
        
        Args:
            workflow_id: The ID of the workflow to execute
            data: The input data for the workflow
            
        Returns:
            The result of the workflow execution
            
        Raises:
            HTTPException: If workflow execution fails
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_url}/workflows/{workflow_id}/execute",
                    headers=self.headers,
                    json=data,
                    timeout=self.timeout
                )
                
                if response.status_code == 400:
                    error_detail = None
                    try:
                        error_json = response.json()
                        if isinstance(error_json, dict):
                            error_detail = error_json.get('message', error_json)
                    except:
                        error_detail = response.text
                    
                    logger.error(f"N8N API returned 400 error: {error_detail}")
                    raise HTTPException(
                        status_code=400,
                        detail=f"Failed to execute workflow: {error_detail}"
                    )
                
                response.raise_for_status()
                result = response.json()
                
                if not isinstance(result, dict):
                    raise ValueError("Invalid response from n8n API: not a JSON object")
                
                logger.info(f"Successfully executed workflow {workflow_id}")
                return result
        except httpx.HTTPError as e:
            logger.error(f"Error executing n8n workflow {workflow_id}: {e}")
            if isinstance(e, httpx.HTTPStatusError):
                status_code = e.response.status_code
                error_detail = None
                try:
                    error_json = e.response.json()
                    if isinstance(error_json, dict):
                        error_detail = error_json.get('message', error_json)
                except:
                    error_detail = e.response.text
                
                raise HTTPException(
                    status_code=status_code,
                    detail=f"Failed to execute workflow: {error_detail}"
                )
            raise HTTPException(
                status_code=500,
                detail=f"Failed to execute workflow: {str(e)}"
            )
        except ValueError as e:
            logger.error(f"Invalid response from n8n API: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=str(e)
            )
        except Exception as e:
            logger.error(f"Unexpected error executing workflow: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to execute workflow: {str(e)}"
            ) 