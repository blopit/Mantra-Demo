"""
Service for managing mantras in the application.
This module handles the logic for:
- Creating new mantras
- Listing available mantras
- Installing mantras for users
- Managing mantra installations
"""

import json
import logging
from uuid import UUID
from typing import List, Dict, Any, Optional, Union
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from datetime import datetime

from src.utils.database import get_db
from src.models.users import Users
from src.models.mantra import Mantra, MantraInstallation
from src.services.n8n_service import N8nService
from src.exceptions import MantraNotFoundError, MantraAlreadyInstalledError
from src.providers.google.transformers import GoogleWorkflowTransformer

logger = logging.getLogger(__name__)

class MantraService:
    """Service for managing mantras and their installations."""
    
    def __init__(self, db_session: AsyncSession, n8n_service: N8nService):
        """Initialize the service.
        
        Args:
            db_session: The database session
            n8n_service: The n8n service for workflow management
        """
        self.db_session = db_session
        self.n8n_service = n8n_service
    
    async def create_mantra(self, name: str, description: str, workflow_json: Dict[str, Any], user_id: str) -> Mantra:
        """
        Create a new mantra
        
        Args:
            name: The name of the mantra
            description: The description of the mantra
            workflow_json: The n8n workflow JSON
            user_id: The ID of the user creating the mantra
            
        Returns:
            The created Mantra object
        """
        try:
            # Validate workflow JSON
            if not workflow_json or not isinstance(workflow_json, dict) or "nodes" not in workflow_json:
                raise ValueError("Invalid workflow JSON: must contain 'nodes' field")
            
            # Check if workflow contains Google service nodes
            contains_google_nodes = False
            google_service_types = ['gmail', 'googlecalendar', 'googledrive', 'googlesheets']
            
            for node in workflow_json.get('nodes', []):
                if node.get('type', '').lower() in google_service_types:
                    contains_google_nodes = True
                    break
            
            # Transform workflow if it contains Google service nodes
            if contains_google_nodes:
                logger.info("Workflow contains Google service nodes. Applying transformation.")
                transformer = GoogleWorkflowTransformer()
                workflow_json = transformer.transform_workflow(workflow_json)
            
            # Now validate the (potentially transformed) workflow
            self.n8n_service._validate_workflow_structure(workflow_json)
            
            # Create new mantra
            mantra = Mantra(
                name=name,
                description=description,
                workflow_json=workflow_json,
                user_id=user_id
            )
            
            self.db_session.add(mantra)
            await self.db_session.commit()
            await self.db_session.refresh(mantra)
            
            return mantra
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except SQLAlchemyError as e:
            await self.db_session.rollback()
            logger.error(f"Database error in create_mantra: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error occurred"
            )
    
    async def get_mantras(self, skip: int = 0, limit: int = 100) -> List[Mantra]:
        """
        Get a list of all active mantras
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of Mantra objects
        """
        try:
            # Build query
            stmt = (
                select(Mantra)
                .where(Mantra.is_active == True)
                .limit(limit)
                .offset(skip)
            )
            logger.debug(f"Executing query: {stmt}")
            
            # Execute query and fetch results
            result = await self.db_session.execute(stmt)
            mantras = result.scalars().all()
            return mantras
        except Exception as e:
            logger.error(f"Error in get_mantras: {str(e)}, {type(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error fetching mantras"
            )
    
    async def get_mantra(self, mantra_id: UUID) -> Mantra:
        """
        Get a mantra by ID
        
        Args:
            mantra_id: The ID of the mantra
            
        Returns:
            Mantra object
        """
        try:
            result = await self.db_session.execute(
                select(Mantra).where(Mantra.id == mantra_id)
            )
            mantra = await result.scalar_one_or_none()
            if not mantra:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Mantra with ID {mantra_id} not found"
                )
            return mantra
        except SQLAlchemyError as e:
            logger.error(f"Database error in get_mantra: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error occurred"
            )
    
    async def install_mantra(self, mantra_id: str, user_id: str, config: Optional[Dict[str, Any]] = None) -> MantraInstallation:
        """Install a mantra for a user.
        
        Args:
            mantra_id: The ID of the mantra to install
            user_id: The ID of the user installing the mantra
            config: Optional configuration for the installation
        
        Returns:
            The created MantraInstallation object
        
        Raises:
            HTTPException: For various error conditions:
                - 404: Mantra not found
                - 400: Already installed, invalid workflow format
                - 500: Internal server error
        """
        n8n_workflow_id = None

        try:
            # Start transaction
            async with self.db_session.begin():
                logger.info(f"Starting mantra installation process for mantra_id={mantra_id}, user_id={user_id}")

                # Get the mantra
                logger.debug(f"Executing query to fetch mantra with ID: {mantra_id}")
                stmt = select(Mantra).where(Mantra.id == mantra_id)
                result = await self.db_session.execute(stmt)
                mantra = result.scalar_one_or_none()

                if not mantra:
                    logger.error(f"Mantra {mantra_id} not found")
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Mantra {mantra_id} not found"
                    )
                logger.debug(f"Successfully fetched mantra: {mantra.id}")

                # Validate workflow format
                logger.debug(f"Validating workflow format for mantra {mantra_id}")
                workflow_data = mantra.workflow_json
                if not workflow_data or not isinstance(workflow_data, dict) or "nodes" not in workflow_data:
                    logger.error(f"Invalid workflow format for mantra {mantra_id}: missing 'nodes' field")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid workflow format: must contain 'nodes' field"
                    )

                # Validate nodes
                if not isinstance(workflow_data["nodes"], list):
                    logger.error(f"Invalid workflow format for mantra {mantra_id}: 'nodes' must be an array")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid workflow format: 'nodes' must be an array"
                    )

                for node in workflow_data["nodes"]:
                    if not isinstance(node, dict) or "type" not in node:
                        logger.error(f"Invalid node format in mantra {mantra_id}: missing required fields")
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Node missing required fields: must contain 'type'"
                        )

                logger.debug(f"Workflow format validation successful for mantra {mantra_id}")

                # Check if already installed
                logger.debug(f"Checking if mantra {mantra_id} is already installed for user {user_id}")
                stmt = select(MantraInstallation).where(
                    and_(
                        MantraInstallation.mantra_id == mantra_id,
                        MantraInstallation.user_id == user_id
                    )
                )
                result = await self.db_session.execute(stmt)
                existing_installation = result.scalar_one_or_none()

                if existing_installation:
                    logger.error(f"Mantra {mantra_id} is already installed for user {user_id}")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Mantra {mantra_id} is already installed for user {user_id}"
                    )

                try:
                    # Check if workflow contains Google service nodes and transform if needed
                    contains_google_nodes = False
                    google_service_types = ['gmail', 'googlecalendar', 'googledrive', 'googlesheets']
                    
                    for node in workflow_data.get('nodes', []):
                        if node.get('type', '').lower() in google_service_types:
                            contains_google_nodes = True
                            break
                    
                    # Transform workflow if it contains Google service nodes
                    if contains_google_nodes:
                        logger.info("Workflow contains Google service nodes. Applying transformation.")
                        transformer = GoogleWorkflowTransformer()
                        workflow_data = transformer.transform_workflow(workflow_data)
                
                    # Create workflow in n8n
                    logger.info(f"Creating n8n workflow for mantra {mantra_id}")
                    logger.debug(f"Workflow JSON content: {workflow_data}")

                    n8n_result = await self.n8n_service.create_workflow(workflow_data)
                    logger.debug(f"n8n workflow creation result: {n8n_result}")

                    # Handle both integer and dictionary response formats
                    n8n_workflow_id = n8n_result["id"] if isinstance(n8n_result, dict) else n8n_result
                    logger.info(f"Created n8n workflow with ID: {n8n_workflow_id}")

                    # Activate the workflow
                    logger.info(f"Activating n8n workflow {n8n_workflow_id}")
                    await self.n8n_service.activate_workflow(n8n_workflow_id)
                    logger.info(f"Successfully activated n8n workflow {n8n_workflow_id}")

                    # Create installation record
                    installation = MantraInstallation(
                        mantra_id=mantra_id,
                        user_id=user_id,
                        config=config or {},
                        n8n_workflow_id=n8n_workflow_id,
                        status="active"
                    )

                    self.db_session.add(installation)
                    await self.db_session.flush()  # Flush to get the ID but don't commit yet

                    logger.info(f"Successfully created installation record with ID: {installation.id}")
                    return installation

                except HTTPException as e:
                    logger.error(f"HTTP error during workflow creation or installation: {str(e)}")
                    if n8n_workflow_id:
                        try:
                            # Try to clean up the n8n workflow if it was created
                            logger.info(f"Attempting to clean up n8n workflow {n8n_workflow_id}")
                            await self.n8n_service.delete_workflow(n8n_workflow_id)
                            logger.info(f"Successfully cleaned up n8n workflow {n8n_workflow_id}")
                        except Exception as cleanup_error:
                            logger.error(f"Failed to clean up n8n workflow {n8n_workflow_id}: {str(cleanup_error)}")
                    raise  # Re-raise the original HTTP exception

                except Exception as e:
                    logger.error(f"Error during workflow creation or installation: {str(e)}")
                    if n8n_workflow_id:
                        try:
                            # Try to clean up the n8n workflow if it was created
                            logger.info(f"Attempting to clean up n8n workflow {n8n_workflow_id}")
                            await self.n8n_service.delete_workflow(n8n_workflow_id)
                            logger.info(f"Successfully cleaned up n8n workflow {n8n_workflow_id}")
                        except Exception as cleanup_error:
                            logger.error(f"Failed to clean up n8n workflow {n8n_workflow_id}: {str(cleanup_error)}")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=str(e)
                    )

        except HTTPException:
            raise  # Re-raise HTTP exceptions as is
        except Exception as e:
            logger.error(f"Unexpected error during mantra installation: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )
    
    async def uninstall_mantra(self, installation_id: str, user_id: str) -> None:
        """Uninstall a mantra for a user.
        
        Args:
            installation_id: The ID of the installation to remove
            user_id: The ID of the user uninstalling the mantra
        
        Raises:
            HTTPException: For various error conditions:
                - 404: Installation not found
                - 403: Not installed by user
                - 500: Internal server error
        """
        try:
            async with self.db_session.begin():
                # Get the installation
                stmt = select(MantraInstallation).where(MantraInstallation.id == installation_id)
                result = await self.db_session.execute(stmt)
                installation = result.scalar_one_or_none()

                if not installation:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Installation {installation_id} not found"
                    )

                if installation.user_id != user_id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Installation {installation_id} not installed by user {user_id}"
                    )

                try:
                    # Delete the n8n workflow
                    if installation.n8n_workflow_id:
                        await self.n8n_service.delete_workflow(installation.n8n_workflow_id)

                    # Delete the installation record
                    await self.db_session.delete(installation)

                except Exception as e:
                    logger.error(f"Error during workflow deletion: {str(e)}")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=str(e)
                    )

        except HTTPException:
            raise  # Re-raise HTTP exceptions as is
        except Exception as e:
            logger.error(f"Unexpected error during mantra uninstallation: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )
    
    async def update_mantra_status(self, installation_id: str, status: str) -> MantraInstallation:
        """
        Update the status of an installed mantra
        
        Args:
            installation_id: The ID of the installation
            status: The new status
            
        Returns:
            Updated MantraInstallation object
        """
        try:
            result = await self.db_session.execute(
                select(MantraInstallation).where(MantraInstallation.id == installation_id)
            )
            installation = await result.scalar_one_or_none()
            if not installation:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Installation with ID {installation_id} not found"
                )
            
            installation.status = status
            await self.db_session.commit()
            await self.db_session.refresh(installation)
            
            return installation
        except HTTPException:
            raise
        except SQLAlchemyError as e:
            await self.db_session.rollback()
            logger.error(f"Database error in update_mantra_status: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error occurred"
            )
    
    async def get_user_installations(self, user_id: str) -> List[MantraInstallation]:
        """
        Get all mantra installations for a user
        
        Args:
            user_id: The ID of the user
            
        Returns:
            List of MantraInstallation objects
        """
        try:
            # Build query
            stmt = (
                select(MantraInstallation)
                .where(MantraInstallation.user_id == user_id)
            )
            logger.debug(f"Executing query: {stmt}")
            
            # Execute query and fetch results
            result = await self.db_session.execute(stmt)
            installations = result.scalars().all()
            return installations
        except Exception as e:
            logger.error(f"Error in get_user_installations: {str(e)}, {type(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error fetching user installations"
            )
    
    async def get_installation(self, installation_id: str) -> Dict:
        """
        Get details of a specific installation.
        
        Args:
            installation_id: ID of the installation
            
        Returns:
            Installation details
            
        Raises:
            HTTPException: If installation not found
        """
        result = await self.db_session.execute(
            select(MantraInstallation)
            .options(selectinload(MantraInstallation.mantra))
            .where(MantraInstallation.id == installation_id)
        )
        installation = result.scalar_one_or_none()
        if not installation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Installation with ID {installation_id} not found"
            )
        
        return {
            "id": str(installation.id),
            "mantra_id": str(installation.mantra_id),
            "mantra_name": installation.mantra.name if installation.mantra else None,
            "status": installation.status,
            "created_at": installation.created_at,
            "n8n_workflow_id": installation.n8n_workflow_id
        }
    
    async def execute_mantra_workflow(self, installation_id: Union[str, UUID], data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a mantra workflow
        
        Args:
            installation_id: The ID of the mantra installation (can be string or UUID)
            data: The input data for the workflow
            
        Returns:
            Result of the workflow execution
        """
        try:
            # Convert string to UUID if needed
            if isinstance(installation_id, str):
                installation_id = UUID(installation_id)
            
            # Get the installation
            result = await self.db_session.execute(
                select(MantraInstallation)
                .options(selectinload(MantraInstallation.mantra))
                .where(MantraInstallation.id == installation_id)
            )
            installation = result.scalar_one_or_none()
            
            if not installation:
                raise HTTPException(
                    status_code=404,
                    detail=f"Installation {installation_id} not found"
                )
            
            # Execute workflow
            try:
                result = await self.n8n_service.execute_workflow(
                    installation.n8n_workflow_id,
                    data
                )
                return {
                    "success": True,
                    "execution_id": result.get("execution_id"),
                    "output": result.get("data", {})
                }
            except Exception as e:
                logger.error(f"Error executing n8n workflow: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Error executing workflow: {str(e)}"
                )
        except HTTPException as e:
            raise e
        except Exception as e:
            logger.error(f"Error executing mantra workflow: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error executing mantra workflow: {str(e)}"
            )
    
    async def list_installed_mantras(self) -> List[MantraInstallation]:
        """List all installed mantras with their associated mantra details."""
        stmt = (
            select(MantraInstallation)
            .options(selectinload(MantraInstallation.mantra))
        )
        result = await self.db_session.execute(stmt)
        installations = result.scalars().all()
        return installations 