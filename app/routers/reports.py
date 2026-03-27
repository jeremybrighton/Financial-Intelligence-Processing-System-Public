"""
Reports router.
GET    /api/v1/reports
POST   /api/v1/reports
GET    /api/v1/reports/{report_id}
PATCH  /api/v1/reports/{report_id}
PATCH  /api/v1/reports/{report_id}/status
"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from app.core.dependencies import require_any_internal_role, require_case_write
from app.schemas.report import ReportCreateRequest, ReportStatusUpdate, ReportUpdateRequest
from app.services import report_service

log = logging.getLogger(__name__)
router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("", summary="List reports")
async def list_reports(
    page: int = 1,
    page_size: int = 20,
    frc_case_id: str = None,
    status: str = None,
    current_user: dict = Depends(require_any_internal_role()),
):
    result = await report_service.list_reports(page, page_size, frc_case_id, status)
    return {"success": True, "data": result}


@router.post("", status_code=201, summary="Create a report draft")
async def create_report(
    body: ReportCreateRequest,
    current_user: dict = Depends(require_case_write()),
):
    try:
        report = await report_service.create_report(body, actor=current_user)
        return {"success": True, "data": report}
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/{report_id}", summary="Get report details")
async def get_report(
    report_id: str,
    current_user: dict = Depends(require_any_internal_role()),
):
    report = await report_service.get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail=f"Report '{report_id}' not found")
    return {"success": True, "data": report}


@router.patch("/{report_id}", summary="Update report content")
async def update_report(
    report_id: str,
    body: ReportUpdateRequest,
    current_user: dict = Depends(require_case_write()),
):
    try:
        report = await report_service.update_report(report_id, body, actor=current_user)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    if not report:
        raise HTTPException(status_code=404, detail=f"Report '{report_id}' not found")
    return {"success": True, "data": report}


@router.patch("/{report_id}/status", summary="Update report status (draft → under_review → finalised)")
async def update_status(
    report_id: str,
    body: ReportStatusUpdate,
    current_user: dict = Depends(require_case_write()),
):
    report = await report_service.update_status(report_id, body, actor=current_user)
    if not report:
        raise HTTPException(status_code=404, detail=f"Report '{report_id}' not found")
    return {"success": True, "data": report}
