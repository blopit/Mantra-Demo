"""
Service for managing n8n workflows.
This module handles the interaction with n8n API for:
- Creating workflows
- Activating/deactivating workflows
- Executing workflow nodes
- Managing workflow lifecycle
"""

import logging
from typing import Dict, Any, Optional, Union, List
import httpx
from fastapi import HTTPException
import aiohttp
import json
import os
from jsonschema import validate, ValidationError
import asyncio
from fastapi import status
import urllib.parse

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
        # Extract base URL for health checks (without /api/v1)
        self.base_url = self.api_url.rsplit('/api/v1', 1)[0]
        self.api_key = api_key
        self.headers = {
            'X-N8N-API-KEY': api_key,
            'Content-Type': 'application/json'
        }
        self.timeout = float(os.getenv("N8N_API_TIMEOUT", "30.0"))
        self.max_retries = int(os.getenv("N8N_MAX_RETRIES", "3"))
        self.retry_delay = float(os.getenv("N8N_RETRY_DELAY", "1.0"))
        
        # Validate environment on initialization
        self.validate_environment()

    def validate_environment(self) -> None:
        """Validate that all required environment variables are set.
        
        Raises:
            ValueError: If any required environment variables are missing
        """
        if not self.api_url or self.api_url.isspace():
            raise ValueError("N8N_API_URL is not configured")
        if not self.api_key or self.api_key.isspace():
            raise ValueError("N8N_API_KEY is not configured")
        
        # Log configuration (masking sensitive data)
        parsed_url = urllib.parse.urlparse(self.api_url)
        netloc_parts = parsed_url.netloc.split('@')
        masked_netloc = netloc_parts[-1] if len(netloc_parts) > 1 else parsed_url.netloc
        masked_url = parsed_url._replace(netloc=masked_netloc).geturl()
        
        logger.info("N8N Service Configuration:", extra={
            "api_url": masked_url,
            "timeout": self.timeout,
            "max_retries": self.max_retries,
            "retry_delay": self.retry_delay
        })

    async def check_connection(self) -> Dict[str, Any]:
        """Check connection to n8n service.
        
        Returns:
            Dict containing connection status and details
            
        Raises:
            HTTPException: If connection check fails
        """
        # Use base URL for health check
        url = f"{self.base_url}/healthz"
        
        logger.info("Checking n8n service connection", extra={
            "url": url,
            "timeout": self.timeout
        })
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(url, headers=self.headers)
                
                # Handle 401 Unauthorized immediately without retrying
                if response.status_code == 401:
                    error_msg = "Unauthorized access to n8n service. Check API key configuration."
                    logger.error(error_msg)
                    raise HTTPException(
                        status_code=401,
                        detail=error_msg
                    )
                
                # For other status codes, raise_for_status and handle in the exception block
                response.raise_for_status()
                
                # For health check, a 200 status code is sufficient
                logger.info("Successfully connected to n8n service")
                return {
                    "is_connected": True,
                    "status": "ok",
                    "response_time_ms": response.elapsed.total_seconds() * 1000
                }
                
            except httpx.HTTPStatusError as e:
                # Handle 401 Unauthorized immediately without retrying
                if e.response.status_code == 401:
                    error_msg = "Unauthorized access to n8n service. Check API key configuration."
                    logger.error(error_msg)
                    raise HTTPException(
                        status_code=401,
                        detail=error_msg
                    ) from e
                
                # For other HTTP errors, retry
                logger.error(f"HTTP error during connection check: {str(e)}", extra={
                    "status_code": e.response.status_code,
                    "response": e.response.text
                })
                
                # Retry with exponential backoff
                for attempt in range(1, self.max_retries):
                    try:
                        await asyncio.sleep(self.retry_delay * (2 ** (attempt - 1)))
                        response = await client.get(url, headers=self.headers)
                        response.raise_for_status()
                        
                        logger.info("Successfully connected to n8n service after retry")
                        return {
                            "is_connected": True,
                            "status": "ok",
                            "response_time_ms": response.elapsed.total_seconds() * 1000
                        }
                    except httpx.HTTPStatusError as retry_e:
                        if retry_e.response.status_code == 401:
                            error_msg = "Unauthorized access to n8n service. Check API key configuration."
                            logger.error(error_msg)
                            raise HTTPException(
                                status_code=401,
                                detail=error_msg
                            ) from retry_e
                        continue
                    except Exception:
                        continue
                
                # If we get here, all retries failed
                raise HTTPException(
                    status_code=e.response.status_code,
                    detail=f"n8n service returned error: {e.response.text}"
                ) from e
                
            except httpx.ConnectError as e:
                # Retry with exponential backoff
                for attempt in range(1, self.max_retries):
                    try:
                        await asyncio.sleep(self.retry_delay * (2 ** (attempt - 1)))
                        response = await client.get(url, headers=self.headers)
                        response.raise_for_status()
                        
                        logger.info("Successfully connected to n8n service after retry")
                        return {
                            "is_connected": True,
                            "status": "ok",
                            "response_time_ms": response.elapsed.total_seconds() * 1000
                        }
                    except Exception:
                        continue
                
                # If we get here, all retries failed
                raise HTTPException(
                    status_code=503,
                    detail=f"Failed to connect to n8n service after {self.max_retries} attempts: {str(e)}"
                ) from e
                
            except httpx.TimeoutException as e:
                # Retry with exponential backoff
                for attempt in range(1, self.max_retries):
                    try:
                        await asyncio.sleep(self.retry_delay * (2 ** (attempt - 1)))
                        response = await client.get(url, headers=self.headers)
                        response.raise_for_status()
                        
                        logger.info("Successfully connected to n8n service after retry")
                        return {
                            "is_connected": True,
                            "status": "ok",
                            "response_time_ms": response.elapsed.total_seconds() * 1000
                        }
                    except Exception:
                        continue
                
                # If we get here, all retries failed
                raise HTTPException(
                    status_code=503,
                    detail=f"Failed to connect to n8n service after {self.max_retries} attempts: {str(e)}"
                ) from e
                
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Unexpected error during connection check: {error_msg}")
                
                # Check for unauthorized errors in the error message
                if "401" in error_msg or "Unauthorized" in error_msg:
                    error_msg = "Unauthorized access to n8n service. Check API key configuration."
                    logger.error(error_msg)
                    raise HTTPException(
                        status_code=401,
                        detail=error_msg
                    ) from e
                
                # Retry with exponential backoff
                for attempt in range(1, self.max_retries):
                    try:
                        await asyncio.sleep(self.retry_delay * (2 ** (attempt - 1)))
                        response = await client.get(url, headers=self.headers)
                        response.raise_for_status()
                        
                        logger.info("Successfully connected to n8n service after retry")
                        return {
                            "is_connected": True,
                            "status": "ok",
                            "response_time_ms": response.elapsed.total_seconds() * 1000
                        }
                    except Exception:
                        continue
                
                # If we get here, all retries failed
                raise HTTPException(
                    status_code=503,
                    detail=f"Failed to connect to n8n service after {self.max_retries} attempts: {error_msg}"
                ) from e

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
        
        # Define Google service node types that need special handling
        google_service_types = {
            'gmail': 'n8n-nodes-base.gmail',
            'googlecalendar': 'n8n-nodes-base.googleCalendar',
            'googledrive': 'n8n-nodes-base.googleDrive',
            'googlesheets': 'n8n-nodes-base.googleSheets'
        }
        
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
            
            # Handle node type transformation
            node_type = node['type']
            node_type_lower = node_type.lower()
            
            if node_type_lower in google_service_types:
                # Transform Google service node types to their n8n equivalents
                node['type'] = google_service_types[node_type_lower]
                logger.info(f"Transformed Google service node type from {node_type} to {node['type']}")
            elif not node_type.startswith('n8n-nodes-base.'):
                # Add n8n-nodes-base prefix for other node types
                node['type'] = f"n8n-nodes-base.{node_type}"
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
        """Prepare a workflow for n8n by adding required fields and removing unsupported ones.
        
        Args:
            workflow_json: The workflow to prepare
            
        Returns:
            The prepared workflow
        """
        # Deep copy to avoid modifying the original
        workflow = json.loads(json.dumps(workflow_json))
        
        # Required fields for n8n workflow - only include what n8n API expects
        prepared_workflow = {
            'name': workflow.get('name', 'Imported Workflow'),
            'nodes': [],
            'connections': workflow.get('connections', {}),
            'settings': workflow.get('settings', {})
        }
        
        # Define Google service node types mapping
        google_service_types = {
            'gmail': 'n8n-nodes-base.gmail',
            'googlecalendar': 'n8n-nodes-base.googleCalendar',
            'googledrive': 'n8n-nodes-base.googleDrive',
            'googlesheets': 'n8n-nodes-base.googleSheets'
        }
        
        # Process each node to ensure it has required fields and correct format
        for node in workflow.get('nodes', []):
            prepared_node = {
                'id': str(node.get('id', '')),
                'name': node.get('name', ''),
                'type': node.get('type', ''),
                'parameters': node.get('parameters', {}),
                'typeVersion': node.get('typeVersion', 1),
                'position': node.get('position', [0, 0])
            }
            
            # Handle node type transformation
            node_type = prepared_node['type']
            node_type_lower = node_type.lower()
            
            if node_type_lower in google_service_types:
                # Transform Google service node types to their n8n equivalents
                prepared_node['type'] = google_service_types[node_type_lower]
                logger.info(f"Transformed Google service node type from {node_type} to {prepared_node['type']}")
            elif not node_type.startswith('n8n-nodes-base.'):
                # Add n8n-nodes-base prefix for other node types
                prepared_node['type'] = f"n8n-nodes-base.{node_type}"
                logger.info(f"Added n8n-nodes-base prefix to node type: {prepared_node['type']}")
            
            prepared_workflow['nodes'].append(prepared_node)
        
        return prepared_workflow
    
    async def list_workflows(self) -> List[Dict[str, Any]]:
        """List all workflows in n8n.
        
        Returns:
            List of workflow objects
            
        Raises:
            HTTPException: If there is an error listing workflows
        """
        # First check connection
        await self.check_connection()
        
        url = f"{self.api_url}/workflows"
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(self.max_retries):
                try:
                    response = await client.get(
                        url,
                        headers=self.headers
                    )
                    response.raise_for_status()
                    workflows = response.json()
                    logger.info(f"Successfully retrieved {len(workflows)} workflows")
                    return workflows
                except httpx.RequestError as e:
                    logger.warning(f"HTTP Request Error on attempt {attempt + 1}: {type(e).__name__} - {str(e)}")
                    if attempt == self.max_retries - 1:
                        logger.error(f"HTTP request error listing n8n workflows after {self.max_retries} attempts: {type(e).__name__} - {str(e)}")
                        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"HTTP request error communicating with n8n: {str(e)}")
                except httpx.HTTPStatusError as e:
                    logger.warning(f"HTTP Status Error on attempt {attempt + 1}: Status {e.response.status_code}")
                    logger.warning(f"Response body: {e.response.text}")
                    if attempt == self.max_retries - 1:
                        logger.error(f"HTTP status error listing n8n workflows after {self.max_retries} attempts: Status {e.response.status_code}")
                        raise HTTPException(status_code=e.response.status_code, detail=f"n8n API error: {e.response.text}")
                await asyncio.sleep(self.retry_delay * (2 ** attempt))

    async def create_workflow(self, workflow_json: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new workflow in n8n.
        
        Args:
            workflow_json: The workflow definition
            
        Returns:
            The created workflow details
            
        Raises:
            HTTPException: If there is an error creating the workflow
        """
        # First check connection
        await self.check_connection()
        
        try:
            prepared_workflow = self._prepare_workflow_for_n8n(workflow_json)
            logger.info(f"Creating n8n workflow with {len(prepared_workflow.get('nodes', []))} nodes")
        except ValueError as e:
            logger.error(f"Workflow preparation failed: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Invalid workflow format: {str(e)}")
        
        url = f"{self.api_url}/workflows"
        
        # Mask API key in headers for logging
        logged_headers = self.headers.copy()
        if 'X-N8N-API-KEY' in logged_headers:
             logged_headers['X-N8N-API-KEY'] = '***MASKED***'

        logger.debug(f"Attempting to create n8n workflow at URL: {url}")
        logger.debug(f"Request Headers: {json.dumps(logged_headers)}")
        logger.debug(f"Request Body: {json.dumps(prepared_workflow, indent=2)}")

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(self.max_retries):
                try:
                    response = await client.post(
                        url,
                        json=prepared_workflow,
                        headers=self.headers
                    )
                    response.raise_for_status()
                    created_workflow = response.json()
                    
                    # If workflow should be active, activate it after creation
                    if workflow_json.get('active', False):
                        try:
                            await self.activate_workflow(created_workflow['id'])
                        except Exception as e:
                            logger.error(f"Failed to activate workflow after creation: {str(e)}")
                            # Don't fail the whole operation if activation fails
                            
                    logger.info(f"Successfully created n8n workflow with ID: {created_workflow.get('id')}")
                    return created_workflow
                except httpx.RequestError as e:
                    logger.warning(f"HTTP Request Error on attempt {attempt + 1}: {type(e).__name__} - {str(e)}")
                    if attempt == self.max_retries - 1:
                        logger.error(f"HTTP request error creating n8n workflow after {self.max_retries} attempts: {type(e).__name__} - {str(e)}")
                        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"HTTP request error communicating with n8n: {str(e)}")
                except httpx.HTTPStatusError as e:
                    logger.warning(f"HTTP Status Error on attempt {attempt + 1}: Status {e.response.status_code}")
                    logger.warning(f"Response body: {e.response.text}")
                    if attempt == self.max_retries - 1:
                        logger.error(f"HTTP status error creating n8n workflow after {self.max_retries} attempts: Status {e.response.status_code}")
                        raise HTTPException(status_code=e.response.status_code, detail=f"n8n API error: {e.response.text}")
                await asyncio.sleep(self.retry_delay * (2 ** attempt))

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