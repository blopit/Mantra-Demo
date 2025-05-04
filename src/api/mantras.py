"""API endpoints for mantra management."""
from typing import Dict, Any, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.utils.database import get_db
from src.models.mantra import Mantra
from src.services.mantra_service import MantraService
from src.services.n8n_service import N8nService
from src.utils.config import get_settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/mantras")

@router.post("/{mantra_id}/install", response_model=Dict[str, Any])
async def install_mantra(
    mantra_id: str,
    user_id: str = Query(..., description="ID of the user installing the mantra"),
    config: Optional[Dict[str, Any]] = None,
    db_session: AsyncSession = Depends(get_db),
):
    """Install a mantra for a user."""
    try:
        logger.info(f"Installing mantra {mantra_id} for user {user_id}")
        settings = get_settings()
        n8n_service = N8nService(settings.N8N_API_URL, settings.N8N_API_KEY)
        service = MantraService(db_session, n8n_service)
        installation = await service.install_mantra(mantra_id, user_id, config)
        logger.info(f"Successfully installed mantra {mantra_id} for user {user_id}")
        return {
            "id": str(installation.id),
            "installation_id": str(installation.id),
            "mantra_id": str(installation.mantra_id),
            "status": installation.status,
            "config": installation.config
        }
    except ValueError as e:
        logger.error(f"Validation error installing mantra {mantra_id} for user {user_id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error installing mantra {mantra_id} for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{mantra_id}/uninstall")
async def uninstall_mantra(
    mantra_id: int,
    db_session: AsyncSession = Depends(get_db),
):
    """Uninstall a mantra."""
    try:
        settings = get_settings()
        n8n_service = N8nService(settings.N8N_API_URL, settings.N8N_API_KEY)
        service = MantraService(db_session, n8n_service)
        await service.uninstall_mantra(mantra_id)
        return {"status": "success"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/installed")
async def list_installed_mantras(
    db_session: AsyncSession = Depends(get_db),
):
    """List all installed mantras."""
    try:
        settings = get_settings()
        n8n_service = N8nService(settings.N8N_API_URL, settings.N8N_API_KEY)
        service = MantraService(db_session, n8n_service)
        installations = await service.list_installed_mantras()
        return [
            {
                "id": str(inst.id),
                "mantra_id": str(inst.mantra_id),
                "mantra_name": inst.mantra.name if inst.mantra else None,
                "status": inst.status,
                "installed_at": inst.installed_at,
                "n8n_workflow_id": inst.n8n_workflow_id
            }
            for inst in installations
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 