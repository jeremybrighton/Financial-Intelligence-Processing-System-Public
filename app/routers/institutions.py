"""
Institution registry router.
POST   /api/v1/institutions
GET    /api/v1/institutions
GET    /api/v1/institutions/{institution_id}
PUT    /api/v1/institutions/{institution_id}
PATCH  /api/v1/institutions/{institution_id}/status
POST   /api/v1/institutions/{institution_id}/api-key
"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from app.core.dependencies import require_admin, require_admin_or_analyst
from app.schemas.institution import (
    ApiKeyResponse,
    InstitutionCreateRequest,
    InstitutionStatusUpdate,
    InstitutionUpdateRequest,
)
from app.services import institution_service

log = logging.getLogger(__name__)
router = APIRouter(prefix="/institutions", tags=["Institutions"])


@router.post("", status_code=201, summary="Register a new institution")
async def create_institution(
    body: InstitutionCreateRequest,
    current_user: dict = Depends(require_admin()),
):
    try:
        inst = await institution_service.create_institution(body, actor=current_user)
        return {"success": True, "data": inst}
    except institution_service.ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("", summary="List registered institutions")
async def list_institutions(
    page: int = 1,
    page_size: int = 20,
    status: str = None,
    institution_type: str = None,
    current_user: dict = Depends(require_admin_or_analyst()),
):
    result = await institution_service.list_institutions(page, page_size, status, institution_type)
    return {"success": True, "data": result}


@router.get("/{institution_id}", summary="Get institution details")
async def get_institution(
    institution_id: str,
    current_user: dict = Depends(require_admin_or_analyst()),
):
    inst = await institution_service.get_institution_by_id(institution_id)
    if not inst:
        raise HTTPException(status_code=404, detail="Institution not found")
    return {"success": True, "data": inst}


@router.put("/{institution_id}", summary="Update institution information")
async def update_institution(
    institution_id: str,
    body: InstitutionUpdateRequest,
    current_user: dict = Depends(require_admin()),
):
    try:
        inst = await institution_service.update_institution(institution_id, body, actor=current_user)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    if not inst:
        raise HTTPException(status_code=404, detail="Institution not found")
    return {"success": True, "data": inst}


@router.patch("/{institution_id}/status", summary="Activate or deactivate an institution")
async def update_status(
    institution_id: str,
    body: InstitutionStatusUpdate,
    current_user: dict = Depends(require_admin()),
):
    inst = await institution_service.update_status(institution_id, body, actor=current_user)
    if not inst:
        raise HTTPException(status_code=404, detail="Institution not found")
    return {"success": True, "data": inst}


@router.post("/{institution_id}/api-key", status_code=201, summary="Generate API key for institution")
async def generate_api_key(
    institution_id: str,
    current_user: dict = Depends(require_admin()),
):
    """
    Generates a new API key for the institution.
    The raw key is returned ONCE — it cannot be retrieved again.
    Only the hash is stored.
    """
    try:
        key_resp = await institution_service.generate_institution_api_key(institution_id, actor=current_user)
        return {"success": True, "data": key_resp}
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
