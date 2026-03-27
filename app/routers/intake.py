"""
Intake API router.
POST /api/v1/intake/cases — receive a reportable case from an institution system

Auth: X-Institution-API-Key header (machine-to-machine, NOT user JWT)
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from app.core.dependencies import get_institution_from_api_key
from app.schemas.intake import IntakeAcknowledgement, IntakeRequest
from app.services import intake_service

log = logging.getLogger(__name__)
router = APIRouter(prefix="/intake", tags=["Case Intake"])


@router.post(
    "/cases",
    status_code=201,
    response_model=IntakeAcknowledgement,
    summary="Submit a reportable case from an institution system",
)
async def submit_case(
    body: IntakeRequest,
    request: Request,
    institution: dict = Depends(get_institution_from_api_key),
):
    """
    Receives a structured suspicious or regulatory case report from a
    registered institution system.

    Authentication: X-Institution-API-Key header.
    This endpoint is for machine-to-machine system calls only.
    It is NOT for manual user submissions.

    On success returns an FRC case ID and acknowledgement.
    """
    try:
        ack = await intake_service.process_intake(
            body=body,
            institution=institution,
            submission_ip=request.client.host if request.client else None,
        )
        return ack
    except Exception as e:
        log.error(f"Intake processing failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to process intake submission")
