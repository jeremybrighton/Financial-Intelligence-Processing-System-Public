"""
Case management router.
GET   /api/v1/cases
GET   /api/v1/cases/{frc_case_id}
PATCH /api/v1/cases/{frc_case_id}/status
PATCH /api/v1/cases/{frc_case_id}
"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from app.core.dependencies import require_any_internal_role, require_case_write
from app.schemas.case import CasePatchRequest, CaseStatusUpdate
from app.services import case_service

log = logging.getLogger(__name__)
router = APIRouter(prefix="/cases", tags=["Case Management"])


@router.get("", summary="List FRC cases")
async def list_cases(
    page: int = 1,
    page_size: int = 20,
    status: str = None,
    report_type: str = None,
    priority: str = None,
    institution_id: str = None,
    current_user: dict = Depends(require_any_internal_role()),
):
    result = await case_service.list_cases(
        page, page_size, status, report_type, priority, institution_id
    )
    return {"success": True, "data": result}


@router.get("/{frc_case_id}", summary="Get case details")
async def get_case(
    frc_case_id: str,
    current_user: dict = Depends(require_any_internal_role()),
):
    case = await case_service.get_case(frc_case_id)
    if not case:
        raise HTTPException(status_code=404, detail=f"Case '{frc_case_id}' not found")
    return {"success": True, "data": case}


@router.patch("/{frc_case_id}/status", summary="Update case status")
async def update_status(
    frc_case_id: str,
    body: CaseStatusUpdate,
    current_user: dict = Depends(require_case_write()),
):
    try:
        case = await case_service.update_status(frc_case_id, body, actor=current_user)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    if not case:
        raise HTTPException(status_code=404, detail=f"Case '{frc_case_id}' not found")
    return {"success": True, "data": case}


@router.patch("/{frc_case_id}", summary="Update case summary, priority, or notes")
async def patch_case(
    frc_case_id: str,
    body: CasePatchRequest,
    current_user: dict = Depends(require_case_write()),
):
    try:
        case = await case_service.patch_case(frc_case_id, body, actor=current_user)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    if not case:
        raise HTTPException(status_code=404, detail=f"Case '{frc_case_id}' not found")
    return {"success": True, "data": case}
