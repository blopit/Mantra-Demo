"""
Service for managing n8n workflows.
This module handles the interaction with n8n API for:
- Creating workflows
- Activating/deactivating workflows
- Executing workflow nodes
- Managing workflow lifecycle
"""

import logging
from typing import Dict, Any, Optional
import httpx
from fastapi import HTTPException
import aiohttp

logger = logging.getLogger(__name__)

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
    
    async def create_workflow(self, workflow_json: Dict[str, Any]) -> int:
        """Create a new workflow in n8n.
        
        Args:
            workflow_json: The workflow definition
            
        Returns:
            The ID of the created workflow
            
        Raises:
            HTTPException: If workflow creation fails
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_url}/workflows",
                    headers=self.headers,
                    json=workflow_json
                )
                response.raise_for_status()
                return response.json()['id']
        except httpx.HTTPError as e:
            logger.error(f"Error creating n8n workflow: {e}")
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
                    headers=self.headers
                )
                response.raise_for_status()
        except httpx.HTTPError as e:
            logger.error(f"Error activating n8n workflow {workflow_id}: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to activate n8n workflow: {str(e)}"
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
                    headers=self.headers
                )
                response.raise_for_status()
        except httpx.HTTPError as e:
            logger.error(f"Error deactivating n8n workflow {workflow_id}: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to deactivate n8n workflow: {str(e)}"
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
                    headers=self.headers
                )
                response.raise_for_status()
        except httpx.HTTPError as e:
            logger.error(f"Error deleting n8n workflow {workflow_id}: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to delete n8n workflow: {str(e)}"
            )
    
    def parse_workflow(self, workflow_json: Dict[str, Any]) -> Dict[str, Any]:
        """Parse and validate a workflow definition.
        
        Args:
            workflow_json: The workflow definition to parse
            
        Returns:
            The parsed workflow with nodes and connections
            
        Raises:
            ValueError: If workflow is invalid
        """
        try:
            nodes = workflow_json.get('nodes', [])
            connections = workflow_json.get('connections', {})
            
            if not nodes:
                raise ValueError("Workflow must contain at least one node")
            
            # Basic validation of node structure
            for node in nodes:
                if not isinstance(node, dict):
                    raise ValueError("Invalid node format")
                if 'id' not in node:
                    raise ValueError("Node missing required 'id' field")
                if 'type' not in node:
                    raise ValueError("Node missing required 'type' field")
            
            return {
                'nodes': nodes,
                'connections': connections
            }
        except Exception as e:
            raise ValueError(f"Invalid workflow format: {str(e)}")
    
    def execute_node(
        self,
        node_id: str,
        data: Dict[str, Any],
        user_id: str,
        workflow_json: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a specific node in a workflow.
        
        Args:
            node_id: The ID of the node to execute
            data: Input data for the node
            user_id: ID of the user executing the node
            workflow_json: The complete workflow definition
            
        Returns:
            The execution results
            
        Raises:
            HTTPException: If node execution fails
        """
        try:
            # Find the node in the workflow
            nodes = workflow_json.get('nodes', [])
            node = next((n for n in nodes if n.get('id') == node_id), None)
            
            if not node:
                raise ValueError(f"Node {node_id} not found in workflow")
            
            # Mock execution for testing
            # In production, this would make an API call to n8n
            return {
                'node_id': node_id,
                'result': {
                    'success': True,
                    'content': {
                        'output': f"Executed {node.get('type')} with data: {data}"
                    }
                }
            }
        except Exception as e:
            logger.error(f"Error executing node {node_id}: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to execute node: {str(e)}"
            )
    
    async def execute_workflow(self, workflow_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a workflow with the given data.
        
        Args:
            workflow_id: The ID of the workflow to execute
            data: The input data for the workflow
            
        Returns:
            The result of the workflow execution
        """
        try:
            url = f"{self.api_url}/workflows/{workflow_id}/execute"
            headers = {
                "X-N8N-API-KEY": self.api_key,
                "Content-Type": "application/json"
            }
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data, headers=headers) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        error_text = await response.text()
                        logger.error(f"Error executing workflow: {error_text}")
                        raise HTTPException(
                            status_code=500,
                            detail=f"Failed to execute workflow: {error_text}"
                        )
        except Exception as e:
            logger.error(f"Error executing workflow: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to execute workflow: {str(e)}"
            ) 