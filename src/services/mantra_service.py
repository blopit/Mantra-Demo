"""
Service for managing mantras in the application.
This module handles the logic for:
- Creating new mantras
- Listing available mantras
- Installing mantras for users
- Managing mantra installations
- Deleting mantras
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
from src.providers.google.transformers.workflow_transformer import GoogleWorkflowTransformer

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
            
        Raises:
            HTTPException: If creation fails
        """
        try:
            # Check if user exists
            result = await self.db_session.execute(
                select(Users).where(Users.id == user_id)
            )
            user = result.scalar_one_or_none()
            if not user:
                logger.error(f"User not found: {user_id}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"User with ID {user_id} not found"
                )

            # Validate workflow JSON
            if not workflow_json or not isinstance(workflow_json, dict) or "nodes" not in workflow_json:
                logger.error(f"Invalid workflow JSON: {workflow_json}")
                raise ValueError("Invalid workflow JSON: must contain 'nodes' field")
            
            # First transform the workflow to convert all trigger nodes to executeWorkflow nodes
            logger.info("Transforming workflow to convert trigger nodes to executeWorkflow nodes")
            transformer = GoogleWorkflowTransformer()
            workflow_json = transformer.transform_workflow(workflow_json)
            
            # Then validate the workflow structure after transformation
            try:
                self.n8n_service._validate_workflow_structure(workflow_json)
            except ValueError as e:
                logger.error(f"Workflow validation failed: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(e)
                )
            
            # Create new mantra
            mantra = Mantra(
                name=name,
                description=description,
                workflow_json=workflow_json,
                user_id=user_id,
                is_active=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            self.db_session.add(mantra)
            await self.db_session.commit()
            await self.db_session.refresh(mantra)
            
            logger.info(f"Successfully created mantra: {mantra.id}")
            return mantra

        except ValueError as e:
            logger.error(f"Validation error in create_mantra: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except SQLAlchemyError as e:
            await self.db_session.rollback()
            logger.error(f"Database error in create_mantra: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error occurred: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Unexpected error in create_mantra: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error creating mantra: {str(e)}"
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
            
            # Refresh the session to ensure we have fresh data
            for mantra in mantras:
                await self.db_session.refresh(mantra)
                
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
            HTTPException: If installation fails
        """
        try:
            # First check n8n connection
            logger.info("Checking n8n service connection before installation")
            try:
                connection_status = await self.n8n_service.check_connection()
                if not connection_status["is_connected"]:
                    error_msg = connection_status.get("error", "Unknown connection error")
                    logger.error(f"n8n service connection failed: {error_msg}")
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail=f"n8n service is not available: {error_msg}"
                    )
            except HTTPException as e:
                # Preserve the original error message from N8N service
                if "n8n service is not available" in str(e.detail):
                    raise
                # Otherwise wrap it in our standard format
                raise HTTPException(
                    status_code=e.status_code,
                    detail=f"n8n service is not available: {e.detail}"
                )
            
            # Get the mantra
            result = await self.db_session.execute(
                select(Mantra).where(Mantra.id == mantra_id)
            )
            mantra = result.scalar_one_or_none()
            if not mantra:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Mantra with ID {mantra_id} not found"
                )
            
            # Check if mantra is already installed for this user
            result = await self.db_session.execute(
                select(MantraInstallation).where(
                    and_(
                        MantraInstallation.mantra_id == mantra_id,
                        MantraInstallation.user_id == user_id,
                        MantraInstallation.is_active == True
                    )
                )
            )
            existing_installation = result.scalar_one_or_none()
            if existing_installation:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Mantra {mantra_id} is already installed for user {user_id}"
                )
            
            # Get workflow data from mantra
            workflow_data = mantra.workflow_json
            
            # Create workflow in n8n
            n8n_workflow = None
            n8n_workflow_id = None
            
            try:
                # Create the workflow
                n8n_workflow = await self.n8n_service.create_workflow(workflow_data)
                if not n8n_workflow:
                    raise ValueError("No workflow returned by n8n")
                
                n8n_workflow_id = n8n_workflow.get("id")
                if not n8n_workflow_id:
                    raise ValueError("No workflow ID returned by n8n")
                
                logger.info(f"Created n8n workflow with ID: {n8n_workflow_id}")
                
                # Activate the workflow
                activation_result = await self.n8n_service.activate_workflow(n8n_workflow_id)
                if not activation_result:
                    raise ValueError("Failed to activate workflow")
                
                logger.info(f"Activated n8n workflow {n8n_workflow_id}")
                
                # Create installation record
                installation = MantraInstallation(
                    mantra_id=mantra_id,
                    user_id=user_id,
                    n8n_workflow_id=n8n_workflow_id,
                    config=config or {},
                    status="active",
                    is_active=True
                )
                
                self.db_session.add(installation)
                await self.db_session.commit()
                await self.db_session.refresh(installation)
                
                return installation
                
            except Exception as e:
                logger.error(f"Error setting up n8n workflow: {str(e)}")
                # Clean up workflow if it was created
                if n8n_workflow_id:
                    try:
                        await self.n8n_service.delete_workflow(n8n_workflow_id)
                    except Exception as cleanup_error:
                        logger.warning(f"Failed to clean up workflow after error: {str(cleanup_error)}")
                
                # Roll back any database changes
                await self.db_session.rollback()
                
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Error setting up n8n workflow: {str(e)}"
                )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error installing mantra: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error installing mantra: {str(e)}"
            )
    
    async def uninstall_mantra(self, installation_id: str, user_id: str) -> None:
        """Uninstall a mantra.
        
        Args:
            installation_id: The ID of the installation to remove
            user_id: The ID of the user uninstalling the mantra
            
        Raises:
            HTTPException: If uninstallation fails
        """
        try:
            # Get the installation
            result = await self.db_session.execute(
                select(MantraInstallation).where(
                    and_(
                        MantraInstallation.id == installation_id,
                        MantraInstallation.user_id == user_id,
                        MantraInstallation.is_active == True
                    )
                )
            )
            installation = result.scalar_one_or_none()
            
            if not installation:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Active installation {installation_id} not found for user {user_id}"
                )
            
            # Deactivate workflow in n8n
            try:
                if installation.n8n_workflow_id:
                    try:
                        await self.n8n_service.deactivate_workflow(installation.n8n_workflow_id)
                        logger.info(f"Deactivated n8n workflow {installation.n8n_workflow_id}")
                    except Exception as e:
                        logger.warning(f"Failed to deactivate n8n workflow: {str(e)}")
                    
                    try:
                        await self.n8n_service.delete_workflow(installation.n8n_workflow_id)
                        logger.info(f"Deleted n8n workflow {installation.n8n_workflow_id}")
                    except Exception as e:
                        logger.warning(f"Failed to delete n8n workflow: {str(e)}")
            except Exception as e:
                logger.warning(f"Error during n8n workflow cleanup: {str(e)}")
                # Continue with installation cleanup even if n8n operations fail
            
            # Mark installation as inactive
            installation.is_active = False
            installation.status = "uninstalled"
            installation.disconnected_at = datetime.utcnow()
            
            await self.db_session.commit()
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error uninstalling mantra: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error uninstalling mantra: {str(e)}"
            )
    
    async def update_mantra_status(self, installation_id: str, status: str) -> MantraInstallation:
        """Update the status of an installed mantra.
        
        Args:
            installation_id: The ID of the installation to update
            status: The new status
            
        Returns:
            The updated MantraInstallation object
            
        Raises:
            HTTPException: If update fails
        """
        try:
            # Get the installation
            result = await self.db_session.execute(
                select(MantraInstallation).where(
                    and_(
                        MantraInstallation.id == installation_id,
                        MantraInstallation.is_active == True
                    )
                )
            )
            installation = result.scalar_one_or_none()
            
            if not installation:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Active installation {installation_id} not found"
                )
            
            # Update status
            installation.status = status
            installation.updated_at = datetime.utcnow()
            
            await self.db_session.commit()
            await self.db_session.refresh(installation)
            
            return installation
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating mantra status: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error updating mantra status: {str(e)}"
            )
    
    async def get_user_installations(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all active mantra installations for a user.
        
        Args:
            user_id: The ID of the user
            
        Returns:
            List of installation dictionaries
            
        Raises:
            HTTPException: If query fails
        """
        try:
            # Get all active installations with their related mantras
            result = await self.db_session.execute(
                select(MantraInstallation)
                .options(selectinload(MantraInstallation.mantra))
                .where(
                    and_(
                        MantraInstallation.user_id == user_id,
                        MantraInstallation.is_active == True
                    )
                )
            )
            installations = result.scalars().all()
            
            # Convert to dictionary format
            installation_list = []
            for installation in installations:
                installation_dict = {
                    "id": str(installation.id),
                    "mantra_id": str(installation.mantra_id),
                    "user_id": installation.user_id,
                    "n8n_workflow_id": installation.n8n_workflow_id,
                    "status": installation.status,
                    "config": installation.config,
                    "installed_at": installation.installed_at.isoformat() if installation.installed_at else None,
                    "disconnected_at": installation.disconnected_at.isoformat() if installation.disconnected_at else None
                }
                
                # Add mantra details if available
                if installation.mantra:
                    installation_dict["mantra"] = {
                        "id": str(installation.mantra.id),
                        "name": installation.mantra.name,
                        "description": installation.mantra.description,
                        "workflow_json": installation.mantra.workflow_json
                    }
                
                installation_list.append(installation_dict)
            
            return installation_list
            
        except Exception as e:
            logger.error(f"Error getting user installations: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error getting user installations: {str(e)}"
            )
    
    async def get_installation(self, installation_id: str) -> Dict:
        """Get a specific mantra installation.
        
        Args:
            installation_id: The ID of the installation
            
        Returns:
            Installation details
            
        Raises:
            HTTPException: If installation not found
        """
        try:
            # Get the installation with mantra details
            result = await self.db_session.execute(
                select(MantraInstallation)
                .options(selectinload(MantraInstallation.mantra))
                .where(
                    and_(
                        MantraInstallation.id == installation_id,
                        MantraInstallation.is_active == True
                    )
                )
            )
            installation = result.scalar_one_or_none()
            
            if not installation:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Active installation {installation_id} not found"
                )
            
            return {
                "id": str(installation.id),
                "mantra_id": str(installation.mantra_id),
                "n8n_workflow_id": installation.n8n_workflow_id,
                "status": installation.status,
                "config": installation.config,
                "installed_at": installation.installed_at,
                "disconnected_at": installation.disconnected_at,
                "mantra": {
                    "id": str(installation.mantra.id),
                    "name": installation.mantra.name,
                    "description": installation.mantra.description
                } if installation.mantra else None
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting installation: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error getting installation: {str(e)}"
            )
    
    async def execute_mantra_workflow(self, installation_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a mantra workflow.
        
        Args:
            installation_id: The ID of the mantra installation
            data: The input data for the workflow
            
        Returns:
            The result of the workflow execution
            
        Raises:
            HTTPException: If workflow execution fails
        """
        try:
            # Get the installation
            installation = await self.get_installation(installation_id)
            if not installation:
                raise HTTPException(
                    status_code=404,
                    detail=f"Installation {installation_id} not found"
                )
            
            # Get the workflow ID
            workflow_id = installation.get("n8n_workflow_id")
            if not workflow_id:
                raise HTTPException(
                    status_code=400,
                    detail="Installation has no associated n8n workflow"
                )
            
            # Execute workflow
            try:
                result = await self.n8n_service.execute_workflow(
                    workflow_id,  # Use string ID
                    data
                )
                return {
                    "success": True,
                    "execution_id": result.get("execution_id"),
                    "output": result.get("data", {})
                }
            except HTTPException as e:
                if e.status_code == 404:
                    # If execution fails with 404, try to reactivate the workflow
                    try:
                        await self.n8n_service.activate_workflow(workflow_id)
                        # Retry execution after reactivation
                        result = await self.n8n_service.execute_workflow(
                            workflow_id,
                            data
                        )
                        return {
                            "success": True,
                            "execution_id": result.get("execution_id"),
                            "output": result.get("data", {})
                        }
                    except Exception as retry_e:
                        logger.error(f"Error executing workflow after reactivation: {str(retry_e)}")
                        raise HTTPException(
                            status_code=500,
                            detail=f"Error executing workflow after reactivation: {str(retry_e)}"
                        )
                raise e
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
                detail=f"Error executing workflow: {str(e)}"
            )
    
    async def list_installed_mantras(self) -> List[MantraInstallation]:
        """Get all active mantra installations.
        
        Returns:
            List of MantraInstallation objects
            
        Raises:
            HTTPException: If query fails
        """
        try:
            # Get all active installations
            result = await self.db_session.execute(
                select(MantraInstallation)
                .options(selectinload(MantraInstallation.mantra))
                .where(MantraInstallation.is_active == True)
            )
            installations = result.scalars().all()
            
            # Convert to dictionary format
            return [
                {
                    "id": str(installation.id),
                    "mantra_id": str(installation.mantra_id),
                    "user_id": installation.user_id,
                    "n8n_workflow_id": installation.n8n_workflow_id,
                    "status": installation.status,
                    "config": installation.config,
                    "installed_at": installation.installed_at,
                    "disconnected_at": installation.disconnected_at,
                    "mantra": {
                        "id": str(installation.mantra.id),
                        "name": installation.mantra.name,
                        "description": installation.mantra.description
                    } if installation.mantra else None
                }
                for installation in installations
            ]
            
        except Exception as e:
            logger.error(f"Error listing installed mantras: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error listing installed mantras: {str(e)}"
            )
    
    async def delete_mantra(self, mantra_id: Union[str, UUID], user_id: str) -> None:
        """Delete a mantra and all its installations.
        
        Args:
            mantra_id: The ID of the mantra to delete
            user_id: The ID of the user requesting deletion
            
        Raises:
            HTTPException: If deletion fails or user doesn't have permission
        """
        try:
            # Convert string to UUID if needed
            if isinstance(mantra_id, str):
                mantra_id = UUID(mantra_id)
            
            # Get the mantra
            result = await self.db_session.execute(
                select(Mantra).where(Mantra.id == mantra_id)
            )
            mantra = result.scalar_one_or_none()
            
            if not mantra:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Mantra with ID {mantra_id} not found"
                )
            
            # Check if user has permission to delete (must be creator)
            if mantra.user_id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only the creator can delete a mantra"
                )
            
            # Get all active installations
            result = await self.db_session.execute(
                select(MantraInstallation)
                .where(
                    and_(
                        MantraInstallation.mantra_id == mantra_id,
                        MantraInstallation.is_active == True
                    )
                )
            )
            installations = result.scalars().all()
            
            # Uninstall all active installations
            for installation in installations:
                try:
                    await self.uninstall_mantra(str(installation.id), installation.user_id)
                except Exception as e:
                    logger.warning(f"Failed to uninstall mantra installation {installation.id}: {str(e)}")
            
            # Mark mantra as inactive (soft delete)
            mantra.is_active = False
            mantra.updated_at = datetime.utcnow()
            
            await self.db_session.commit()
            
            logger.info(f"Successfully deleted mantra {mantra_id}")
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error deleting mantra: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error deleting mantra: {str(e)}"
            ) 