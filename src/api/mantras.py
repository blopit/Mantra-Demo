"""API endpoints for mantra management."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.utils.database import get_db
from src.models.mantra import Mantra
from src.services.mantra_service import MantraService
from src.services.n8n_service import N8nService
from src.utils.config import get_settings

router = APIRouter(prefix="/api/mantras")

@router.post("/{mantra_id}/install")
async def install_mantra(
    mantra_id: int,
    db_session: AsyncSession = Depends(get_db),
):
    """Install a mantra."""
    try:
        settings = get_settings()
        n8n_service = N8nService(settings.N8N_API_URL, settings.N8N_API_KEY)
        service = MantraService(db_session, n8n_service)
        await service.install_mantra(mantra_id)
        return {"status": "success"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
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
                "created_at": inst.created_at,
                "n8n_workflow_id": inst.n8n_workflow_id
            }
            for inst in installations
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 