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
from typing import List, Dict, Any, Optional
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from src.utils.database import get_db
from src.models.users import Users
from src.models.mantra import Mantra, MantraInstallation
from src.services.n8n_conversion import N8nConversionService

logger = logging.getLogger(__name__)

class MantraService:
    """Service for managing mantras"""
    
    def __init__(self, db: Session = Depends(get_db)):
        self.db = db
        self.n8n_service = N8nConversionService(db)
    
    def create_mantra(self, name: str, description: str, workflow_json: Dict[str, Any], user_id: str) -> Mantra:
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
            self.n8n_service.parse_workflow(workflow_json)
            
            # Create new mantra
            mantra = Mantra(
                name=name,
                description=description,
                workflow_json=workflow_json,
                user_id=user_id
            )
            
            self.db.add(mantra)
            self.db.commit()
            self.db.refresh(mantra)
            
            return mantra
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error in create_mantra: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error occurred"
            )
    
    def get_mantras(self, skip: int = 0, limit: int = 100) -> List[Mantra]:
        """
        Get all available mantras
        
        Args:
            skip: Number of mantras to skip
            limit: Maximum number of mantras to return
            
        Returns:
            List of Mantra objects
        """
        try:
            return self.db.query(Mantra).filter(Mantra.is_active == True).offset(skip).limit(limit).all()
        except SQLAlchemyError as e:
            logger.error(f"Database error in get_mantras: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error occurred"
            )
    
    def get_mantra_by_id(self, mantra_id: str) -> Mantra:
        """
        Get a mantra by ID
        
        Args:
            mantra_id: The ID of the mantra
            
        Returns:
            Mantra object
        """
        try:
            mantra = self.db.query(Mantra).filter(Mantra.id == mantra_id).first()
            if not mantra:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Mantra with ID {mantra_id} not found"
                )
            return mantra
        except SQLAlchemyError as e:
            logger.error(f"Database error in get_mantra_by_id: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error occurred"
            )
    
    def install_mantra(self, mantra_id: str, user_id: str, config: Optional[Dict[str, Any]] = None) -> MantraInstallation:
        """
        Install a mantra for a user
        
        Args:
            mantra_id: The ID of the mantra to install
            user_id: The ID of the user installing the mantra
            config: Optional configuration for the mantra installation
            
        Returns:
            The created MantraInstallation object
        """
        try:
            # Check if mantra exists
            mantra = self.get_mantra_by_id(mantra_id)
            
            # Check if user exists
            user = self.db.query(Users).filter(Users.id == user_id).first()
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"User with ID {user_id} not found"
                )
            
            # Check if mantra is already installed
            existing = self.db.query(MantraInstallation).filter(
                MantraInstallation.mantra_id == mantra_id,
                MantraInstallation.user_id == user_id
            ).first()
            
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Mantra {mantra.name} is already installed for this user"
                )
            
            # Create installation
            installation = MantraInstallation(
                mantra_id=mantra_id,
                user_id=user_id,
                config=config
            )
            
            self.db.add(installation)
            self.db.commit()
            self.db.refresh(installation)
            
            return installation
        except HTTPException:
            raise
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error in install_mantra: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error occurred"
            )
    
    def uninstall_mantra(self, installation_id: str) -> bool:
        """
        Uninstall a mantra
        
        Args:
            installation_id: The ID of the installation
            
        Returns:
            True if successful
        """
        try:
            installation = self.db.query(MantraInstallation).filter(MantraInstallation.id == installation_id).first()
            if not installation:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Installation with ID {installation_id} not found"
                )
            
            self.db.delete(installation)
            self.db.commit()
            
            return True
        except HTTPException:
            raise
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error in uninstall_mantra: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error occurred"
            )
    
    def update_mantra_status(self, installation_id: str, status: str) -> MantraInstallation:
        """
        Update the status of an installed mantra
        
        Args:
            installation_id: The ID of the installation
            status: The new status
            
        Returns:
            Updated MantraInstallation object
        """
        try:
            installation = self.db.query(MantraInstallation).filter(MantraInstallation.id == installation_id).first()
            if not installation:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Installation with ID {installation_id} not found"
                )
            
            installation.status = status
            self.db.commit()
            self.db.refresh(installation)
            
            return installation
        except HTTPException:
            raise
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error in update_mantra_status: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error occurred"
            )
    
    def get_user_mantras(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all mantras for a user
        
        Args:
            user_id: The ID of the user
            
        Returns:
            A list of mantras
        """
        try:
            installations = self.db.query(MantraInstallation).filter(MantraInstallation.user_id == user_id).all()
            
            result = []
            for installation in installations:
                mantra = installation.mantra
                result.append({
                    "installation_id": str(installation.id),
                    "status": installation.status,
                    "installed_at": installation.installed_at,
                    "config": installation.config,
                    "mantra": {
                        "id": str(mantra.id),
                        "name": mantra.name,
                        "description": mantra.description
                    }
                })
            
            return result
        except SQLAlchemyError as e:
            logger.error(f"Database error in get_user_mantras: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error occurred"
            )
    
    def execute_mantra_workflow(self, installation_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a mantra workflow
        
        Args:
            installation_id: The ID of the mantra installation
            data: The input data for the workflow
            
        Returns:
            Result of the workflow execution
        """
        try:
            # Get the installation
            installation = self.db.query(MantraInstallation).filter(MantraInstallation.id == installation_id).first()
            if not installation:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Installation with ID {installation_id} not found"
                )
            
            # Get the mantra
            mantra = installation.mantra
            
            # Parse the workflow to find the trigger node
            workflow_json = mantra.workflow_json
            parsed = self.n8n_service.parse_workflow(workflow_json)
            nodes = parsed['nodes']
            connections = parsed['connections']
            
            # Find trigger nodes
            trigger_nodes = [node for node in nodes if 'Trigger' in node.get('type', '')]
            if not trigger_nodes:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No trigger node found in workflow"
                )
            
            trigger_node = trigger_nodes[0]
            trigger_id = trigger_node.get('id')
            
            # Find nodes connected to the trigger
            connected_nodes = []
            if trigger_id in connections:
                for connection in connections[trigger_id].get('main', []):
                    for node_connection in connection:
                        connected_node_id = node_connection.get('node')
                        connected_node = next((n for n in nodes if n.get('id') == connected_node_id), None)
                        if connected_node:
                            connected_nodes.append(connected_node)
            
            if not connected_nodes:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No nodes connected to trigger in workflow"
                )
            
            # Execute each connected node in sequence
            results = []
            current_data = data
            
            for node in connected_nodes:
                node_result = self.n8n_service.execute_node(
                    node_id=node.get('id'),
                    data=current_data,
                    user_id=installation.user_id,
                    workflow_json=workflow_json
                )
                
                results.append(node_result)
                
                # Update current_data for next node
                if node_result.get('result', {}).get('success', False):
                    current_data = node_result.get('result', {}).get('content', current_data)
            
            return {
                "installation_id": str(installation.id),
                "mantra_id": str(mantra.id),
                "mantra_name": mantra.name,
                "results": results
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error executing mantra workflow: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error executing mantra workflow: {str(e)}"
            ) 