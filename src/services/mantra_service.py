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
from sqlalchemy.exc import SQLAlchemyError
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
            
            self.n8n_service.parse_workflow(workflow_json)
            
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
        Get all available mantras
        
        Args:
            skip: Number of mantras to skip
            limit: Maximum number of mantras to return
            
        Returns:
            List of Mantra objects
        """
        try:
            result = await self.db_session.execute(
                select(Mantra)
                .where(Mantra.is_active == True)
                .offset(skip)
                .limit(limit)
            )
            return result.scalars().all()
        except SQLAlchemyError as e:
            logger.error(f"Database error in get_mantras: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error occurred"
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
            mantra = result.scalar_one_or_none()
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
        """Install a mantra for a user
        
        Args:
            mantra_id: The ID of the mantra to install
            user_id: The ID of the user installing the mantra
            config: Optional configuration for the installation
            
        Returns:
            The created MantraInstallation object
        """
        try:
            # Get the mantra
            result = await self.db_session.execute(
                select(Mantra).where(Mantra.id == mantra_id)
            )
            mantra = result.scalar_one_or_none()
            if not mantra:
                raise MantraNotFoundError(f"Mantra {mantra_id} not found")
                
            # Validate workflow format
            if not mantra.workflow_json or "nodes" not in mantra.workflow_json:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid workflow format: must contain 'nodes' field"
                )
                
            # Check if already installed
            result = await self.db_session.execute(
                select(MantraInstallation)
                .where(
                    and_(
                        MantraInstallation.mantra_id == mantra_id,
                        MantraInstallation.user_id == user_id
                    )
                )
            )
            existing = result.scalar_one_or_none()
            if existing:
                raise MantraAlreadyInstalledError(f"Mantra {mantra_id} is already installed for user {user_id}")
                
            # Create workflow in n8n
            try:
                n8n_result = await self.n8n_service.create_workflow(mantra.workflow_json)
                # Handle both integer and dictionary response formats
                workflow_id = n8n_result["id"] if isinstance(n8n_result, dict) else n8n_result
                
                # Activate the workflow
                await self.n8n_service.activate_workflow(workflow_id)
            except Exception as e:
                logger.error(f"Error creating n8n workflow: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Error creating n8n workflow: {str(e)}"
                )
                
            # Create installation
            installation = MantraInstallation(
                mantra_id=mantra_id,
                user_id=user_id,
                status="active",
                config=config,
                n8n_workflow_id=workflow_id
            )
            self.db_session.add(installation)
            await self.db_session.commit()
            await self.db_session.refresh(installation)
            
            return installation
            
        except (MantraNotFoundError, MantraAlreadyInstalledError, HTTPException):
            raise
        except Exception as e:
            logger.error(f"Error installing mantra: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error installing mantra: {str(e)}"
            )
    
    async def uninstall_mantra(self, installation_id: UUID, user_id: str) -> None:
        """Uninstall a mantra for a user.
    
        Args:
            installation_id: The ID of the installation to uninstall
            user_id: The ID of the user uninstalling the mantra
    
        Raises:
            MantraNotFoundError: If the mantra installation doesn't exist
            HTTPException: If there's an error deleting the workflow
        """
        try:
            # Find installation
            result = await self.db_session.execute(
                select(MantraInstallation).where(
                    MantraInstallation.id == installation_id,
                    MantraInstallation.user_id == user_id
                )
            )
            installation = result.scalar_one_or_none()
            if not installation:
                raise MantraNotFoundError(
                    f"No installation found for id {installation_id} and user {user_id}"
                )
            
            # Delete n8n workflow if it exists
            if installation.n8n_workflow_id:
                try:
                    await self.n8n_service.delete_workflow(installation.n8n_workflow_id)
                except Exception as e:
                    logger.error(f"Error deleting n8n workflow {installation.n8n_workflow_id}: {str(e)}")
                    raise HTTPException(
                        status_code=500,
                        detail=f"Failed to delete n8n workflow: {str(e)}"
                    )
                
            # Delete the installation
            await self.db_session.delete(installation)
            await self.db_session.commit()
        except (MantraNotFoundError, HTTPException):
            raise
        except Exception as e:
            logger.error(f"Error uninstalling mantra: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error uninstalling mantra: {str(e)}"
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
            installation = result.scalar_one_or_none()
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
    
    async def get_user_installations(self, user_id: str) -> List[Dict]:
        """
        Get all mantras for a user
        
        Args:
            user_id: The ID of the user
            
        Returns:
            A list of mantras
        """
        result = await self.db_session.execute(
            select(MantraInstallation)
            .options(selectinload(MantraInstallation.mantra))
            .where(MantraInstallation.user_id == user_id)
        )
        installations = result.scalars().all()
        
        return [
            {
                "id": str(inst.id),
                "mantra_id": str(inst.mantra_id),
                "mantra_name": inst.mantra.name if inst.mantra else None,
                "status": inst.status,
                "created_at": inst.created_at,
                "n8n_workflow_id": inst.n8n_workflow_id
            }
            for inst in installations
        ]
    
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