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
import time
from jsonschema import validate, ValidationError
import asyncio
from fastapi import status
import urllib.parse
from src.providers.google.transformers.workflow_transformer import GoogleWorkflowTransformer

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
            "type": "object"
        }
    }
}

# Mapping of Google service types to n8n node types
google_service_types = {
    'gmail': 'n8n-nodes-base.gmail',
    'googlecalendar': 'n8n-nodes-base.googleCalendar',
    'googledrive': 'n8n-nodes-base.googleDrive',
    'googlesheets': 'n8n-nodes-base.googleSheets'
}

class N8nService:
    """Service for managing n8n workflows."""
    
    def __init__(self, api_url: str = None, api_key: str = None):
        """Initialize the service.
        
        Args:
            api_url: The n8n API URL
            api_key: The n8n API key
        """
        self.api_url = api_url or os.getenv('N8N_API_URL')
        self.api_key = api_key or os.getenv('N8N_API_KEY')
        
        if not self.api_url:
            raise ValueError("N8N_API_URL environment variable is required")
        if not self.api_key:
            raise ValueError("N8N_API_KEY environment variable is required")
            
        # Extract base URL for health checks (without /api/v1)
        self.base_url = self.api_url.rsplit('/api/v1', 1)[0]
            
        self.headers = {
            "accept": "application/json",
            "X-N8N-API-KEY": self.api_key
        }
        
        # Initialize workflow transformer
        self.workflow_transformer = GoogleWorkflowTransformer()
        
        # Configure timeouts and retries
        self.timeout = float(os.getenv("N8N_API_TIMEOUT", "30.0"))
        self.max_retries = int(os.getenv("N8N_MAX_RETRIES", "3"))
        self.retry_delay = float(os.getenv("N8N_RETRY_DELAY", "1.0"))
        
        logger.info(f"Initialized N8nService with API URL: {self.api_url}")
    
    async def check_connection(self) -> Dict[str, Any]:
        """Check connection to n8n API.
        
        Returns:
            Dict with connection status
        """
        try:
            start_time = time.time()
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/healthz",
                    headers=self.headers
                )
                response.raise_for_status()
                
                end_time = time.time()
                response_time_ms = (end_time - start_time) * 1000
                
                return {
                    "is_connected": True,
                    "status": "ok",
                    "response_time_ms": response_time_ms
                }
                
        except Exception as e:
            logger.error(f"Error checking n8n connection: {str(e)}")
            return {
                "is_connected": False,
                "status": "error",
                "error": str(e)
            }
    
    def parse_workflow(self, workflow_json: Dict[str, Any]) -> Dict[str, Any]:
        """Parse and validate a workflow JSON.
        
        Args:
            workflow_json: The workflow JSON to parse
            
        Returns:
            The parsed and validated workflow JSON
            
        Raises:
            ValueError: If the workflow JSON is invalid
        """
        try:
            # Validate against schema
            validate(instance=workflow_json, schema=WORKFLOW_SCHEMA)
            
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
            
        except ValidationError as e:
            logger.error(f"Workflow validation error: {str(e)}")
            raise ValueError(f"Invalid workflow JSON: {str(e)}")
        except Exception as e:
            logger.error(f"Error parsing workflow: {str(e)}")
            raise
    
    def _validate_workflow_structure(self, workflow: Dict[str, Any]) -> None:
        """Validate the structure of a workflow.
        
        Args:
            workflow: The workflow to validate
            
        Raises:
            ValueError: If the workflow structure is invalid
        """
        if not isinstance(workflow, dict):
            raise ValueError("Workflow must be a dictionary")
            
        if "nodes" not in workflow:
            raise ValueError("Workflow must contain 'nodes' field")
            
        if not isinstance(workflow["nodes"], list):
            raise ValueError("Workflow nodes must be a list")
            
        # Check for required node fields
        for node in workflow["nodes"]:
            if not isinstance(node, dict):
                raise ValueError("Each node must be a dictionary")
                
            if "id" not in node:
                raise ValueError("Each node must have an 'id' field")
                
            if "type" not in node:
                raise ValueError("Each node must have a 'type' field")
                
            if "parameters" not in node:
                raise ValueError("Each node must have a 'parameters' field")
            
        logger.info(f"Successfully validated workflow with {len(workflow['nodes'])} nodes")
    
    def _prepare_workflow_for_n8n(self, workflow_json: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare a workflow for n8n by adding required fields and removing unsupported ones.
        
        Args:
            workflow_json: The workflow to prepare
            
        Returns:
            The prepared workflow
        """
        logger.info("Preparing workflow for n8n")
        logger.info(f"Input workflow: {json.dumps(workflow_json, indent=2)}")
        
        # Deep copy to avoid modifying the original
        workflow = json.loads(json.dumps(workflow_json))
        
        # Transform the workflow using the GoogleWorkflowTransformer
        workflow = self.workflow_transformer.transform_workflow(workflow)
        
        # Required fields for n8n workflow - only include what n8n API expects
        prepared_workflow = {
            'name': workflow.get('name', 'Imported Workflow'),
            'nodes': workflow.get('nodes', []),
            'connections': workflow.get('connections', {}),
            'settings': {
                'saveExecutionProgress': True,
                'saveManualExecutions': True,
                **(workflow.get('settings', {}))
            },
            'staticData': None
        }
        
        logger.info(f"Final prepared workflow: {json.dumps(prepared_workflow, indent=2)}")
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
            The created workflow
            
        Raises:
            HTTPException: If there is an error creating the workflow
        """
        logger.info("Creating new n8n workflow")
        
        # First validate and prepare the workflow
        try:
            self._validate_workflow_structure(workflow_json)
            workflow = self._prepare_workflow_for_n8n(workflow_json)
            logger.info(f"Number of nodes in workflow: {len(workflow.get('nodes', []))}")
        except ValidationError as e:
            error_msg = f"Invalid workflow structure: {str(e)}"
            logger.error(error_msg)
            raise HTTPException(
                status_code=400,
                detail=error_msg
            ) from e
        except Exception as e:
            error_msg = f"Error preparing workflow: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=error_msg
            ) from e
        
        url = f"{self.api_url}/workflows"
        client = httpx.AsyncClient(timeout=self.timeout)
        
        try:
            for attempt in range(1, self.max_retries + 1):
                try:
                    response = await client.post(
                        url,
                        headers=self.headers,
                        json=workflow
                    )
                    
                    if response.status_code == 401:
                        error_msg = "Unauthorized access to n8n service. Check API key configuration."
                        logger.error(error_msg)
                        raise HTTPException(
                            status_code=401,
                            detail=error_msg
                        )
                    
                    response.raise_for_status()
                    created_workflow = response.json()
                    
                    # Always try to activate the workflow after creation
                    try:
                        await self.activate_workflow(created_workflow['id'])
                        logger.info(f"Successfully activated workflow {created_workflow['id']}")
                    except Exception as e:
                        logger.error(f"Failed to activate workflow after creation: {str(e)}", exc_info=True)
                        # Don't fail the whole operation if activation fails
                    
                    logger.info(f"Successfully created n8n workflow with ID: {created_workflow.get('id')}")
                    return created_workflow
                    
                except httpx.HTTPStatusError as e:
                    logger.warning(f"HTTP Status Error on attempt {attempt}: Status {e.response.status_code}")
                    logger.warning(f"Response body: {e.response.text}")
                    
                    if attempt == self.max_retries:
                        error_msg = f"HTTP status error creating n8n workflow after {attempt} attempts: Status {e.response.status_code}"
                        logger.error(error_msg)
                        raise HTTPException(
                            status_code=500,
                            detail=error_msg
                        ) from e
                    
                    await asyncio.sleep(self.retry_delay * attempt)
                
        except Exception as e:
            error_msg = f"Error creating n8n workflow: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=error_msg
            ) from e
            
        finally:
            await client.aclose()

    async def activate_workflow(self, workflow_id: Union[str, int]) -> bool:
        """Activate a workflow in n8n.
        
        Args:
            workflow_id: The ID of the workflow to activate
            
        Returns:
            True if activation was successful
            
        Raises:
            HTTPException: If there is an error activating the workflow
        """
        try:
            # First check if workflow exists and get its current state
            workflow = await self.get_workflow(workflow_id)
            if not workflow:
                raise HTTPException(
                    status_code=404,
                    detail=f"Workflow {workflow_id} not found"
                )
            
            # If already active, return success
            if workflow.get('active', False):
                logger.info(f"Workflow {workflow_id} is already active")
                return True
            
            # Activate the workflow with retries
            async with httpx.AsyncClient() as client:
                for attempt in range(self.max_retries):
                    try:
                        # Send activation request
                        response = await client.post(
                            f"{self.api_url}/workflows/{workflow_id}/activate",
                            headers=self.headers,
                            timeout=self.timeout
                        )
                        
                        # Log response details for debugging
                        logger.debug(f"Activation attempt {attempt + 1} response status: {response.status_code}")
                        logger.debug(f"Response headers: {response.headers}")
                        logger.debug(f"Response body: {response.text}")
                        
                        if response.status_code == 400:
                            # Parse error response
                            error_detail = None
                            try:
                                error_json = response.json()
                                if isinstance(error_json, dict):
                                    error_detail = error_json.get('message', error_json)
                            except:
                                error_detail = response.text
                            
                            logger.error(f"N8N API returned 400 error: {error_detail}")
                            if attempt == self.max_retries - 1:
                                raise HTTPException(
                                    status_code=400,
                                    detail=f"Failed to activate workflow: {error_detail}"
                                )
                        else:
                            try:
                                response.raise_for_status()
                                logger.info(f"Successfully activated workflow {workflow_id}")
                                return True
                            except httpx.HTTPError as e:
                                if attempt == self.max_retries - 1:
                                    logger.error(f"Failed to activate workflow after {self.max_retries} attempts")
                                    raise HTTPException(
                                        status_code=e.response.status_code if hasattr(e, 'response') else 500,
                                        detail=f"Error activating workflow: {str(e)}"
                                    )
                                logger.warning(f"Activation attempt {attempt + 1} failed, retrying...")
                                
                        # Wait before retrying with exponential backoff
                        if attempt < self.max_retries - 1:
                            await asyncio.sleep(self.retry_delay * (2 ** attempt))
                            
                    except Exception as e:
                        if attempt == self.max_retries - 1:
                            logger.error(f"Failed to activate workflow after {self.max_retries} attempts")
                            raise HTTPException(
                                status_code=500,
                                detail=f"Error activating workflow: {str(e)}"
                            )
                        logger.warning(f"Activation attempt {attempt + 1} failed, retrying...")
                        await asyncio.sleep(self.retry_delay * (2 ** attempt))
                
                return False
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error activating workflow {workflow_id}: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error activating workflow: {str(e)}"
            )
    
    async def deactivate_workflow(self, workflow_id: Union[str, int]) -> None:
        """Deactivate a workflow in n8n.
        
        Args:
            workflow_id: The ID of the workflow to deactivate (can be string or integer)
            
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
    
    async def delete_workflow(self, workflow_id: Union[str, int]) -> None:
        """Delete a workflow from n8n.
        
        Args:
            workflow_id: The ID of the workflow to delete (can be string or integer)
            
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
    
    async def get_webhook_url(self, workflow_id: Union[str, int]) -> Optional[str]:
        """Get the webhook URL for a workflow if it has a webhook trigger node.
        This method always returns None since all trigger nodes are transformed to executeWorkflow nodes.
        
        Args:
            workflow_id: The ID of the workflow
            
        Returns:
            None since webhooks are not used
        """
        return None

    async def execute_workflow(self, workflow_id: Union[str, int], data: Dict[str, Any]) -> Dict[str, Any]:
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
            # First check if workflow exists and get its current state
            workflow = await self.get_workflow(workflow_id)
            if not workflow:
                logger.error(f"Workflow {workflow_id} not found")
                raise HTTPException(
                    status_code=404,
                    detail=f"Workflow {workflow_id} not found"
                )
            
            # Check if workflow is active
            is_active = workflow.get("active", False)
            
            # If not active, activate it first
            if not is_active:
                logger.info(f"Activating workflow {workflow_id}")
                await self.activate_workflow(workflow_id)
            else:
                logger.info(f"Workflow {workflow_id} is already active")
            
            # Use the base webhook URL
            webhook_url = "https://blopit.app.n8n.cloud/webhook/execute"
            logger.info(f"Using webhook URL: {webhook_url}")
            
            # Prepare webhook data with workflowId
            webhook_data = {
                "workflowId": str(workflow_id),
                "data": data
            }
            
            headers = {
                "accept": "application/json",
                "Content-Type": "application/json"
            }
            
            # Execute the workflow via webhook
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    webhook_url,
                    headers=headers,
                    json=webhook_data,
                    timeout=30.0
                )
                
                if response.status_code == 404:
                    # Try reactivating the workflow
                    logger.info("Workflow returned 404, attempting to reactivate workflow")
                    await self.activate_workflow(workflow_id)
                    
                    # Try execution again after reactivation
                    response = await client.post(
                        webhook_url,
                        headers=headers,
                        json=webhook_data,
                        timeout=30.0
                    )
                
                if response.status_code >= 400:
                    error_msg = f"Failed to execute workflow: {response.text}"
                    logger.error(error_msg)
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=error_msg
                    )
                
                result = response.json()
                return {
                    "success": True,
                    "execution_id": result.get("executionId"),
                    "data": result.get("data", {})
                }
                
        except httpx.HTTPError as e:
            error_msg = f"HTTP error executing workflow: {str(e)}"
            logger.error(error_msg)
            raise HTTPException(
                status_code=500,
                detail=error_msg
            )
        except Exception as e:
            error_msg = f"Error executing workflow: {str(e)}"
            logger.error(error_msg)
            raise HTTPException(
                status_code=500,
                detail=error_msg
            )

    async def get_workflow(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get a workflow from n8n.
        
        Args:
            workflow_id: The ID of the workflow to get
            
        Returns:
            The workflow data if found, None if not found
            
        Raises:
            HTTPException: If the request fails
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.api_url}/workflows/{workflow_id}",
                    headers=self.headers
                )
                
                if response.status_code == 404:
                    return None
                
                response.raise_for_status()
                return response.json()
                
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            logger.error(f"HTTP error getting n8n workflow {workflow_id}: {str(e)}")
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Error getting n8n workflow: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Error getting n8n workflow {workflow_id}: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error getting n8n workflow: {str(e)}"
            )

    def _is_trigger_node(self, node: Dict[str, Any]) -> bool:
        """Check if a node is a trigger node.
        
        Args:
            node: The node to check
            
        Returns:
            True if the node is a trigger node, False otherwise
        """
        node_type = node.get('type', '').lower()
        return ('trigger' in node_type or 
                node_type == 'n8n-nodes-base.webhook' or 
                node_type == 'n8n-nodes-base.scheduletrigger' or
                node_type == 'scheduletrigger') 