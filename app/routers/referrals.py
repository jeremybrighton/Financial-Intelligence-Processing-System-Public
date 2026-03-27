"""
Referrals router.
GET    /api/v1/referrals
POST   /api/v1/referrals
GET    /api/v1/referrals/{referral_id}
PATCH  /api/v1/referrals/{referral_id}/status
"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from app.core.dependencies import require_any_internal_role, require_case_write
from app.schemas.referral import ReferralCreateRequest, ReferralStatusUpdate, REFERRAL_DESTINATIONS
from app.services import referral_service

log = logging.getLogger(__name__)
router = APIRouter(prefix="/referrals", tags=["Referrals"])


@router.get("", summary="List referrals")
async def list_referrals(
    page: int = 1,
    page_size: int = 20,
    frc_case_id: str = None,
    status: str = None,
    destination_body: str = None,
    case_type: str = None,
    current_user: dict = Depends(require_any_internal_role()),
):
    result = await referral_service.list_referrals(
        page, page_size, frc_case_id, status, destination_body, case_type
    )
    return {"success": True, "data": result}


@router.post("", status_code=201, summary="Create a referral")
async def create_referral(
    body: ReferralCreateRequest,
    current_user: dict = Depends(require_case_write()),
):
    try:
        ref = await referral_service.create_referral(body, actor=current_user)
        return {"success": True, "data": ref}
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/{referral_id}", summary="Get referral details")
async def get_referral(
    referral_id: str,
    current_user: dict = Depends(require_any_internal_role()),
):
    ref = await referral_service.get_referral(referral_id)
    if not ref:
        raise HTTPException(status_code=404, detail=f"Referral '{referral_id}' not found")
    return {"success": True, "data": ref}


@router.patch("/{referral_id}/status", summary="Update referral status")
async def update_status(
    referral_id: str,
    body: ReferralStatusUpdate,
    current_user: dict = Depends(require_case_write()),
):
    ref = await referral_service.update_status(referral_id, body, actor=current_user)
    if not ref:
        raise HTTPException(status_code=404, detail=f"Referral '{referral_id}' not found")
    return {"success": True, "data": ref}


@router.get("/meta/destinations", summary="List all valid destination bodies")
async def list_destinations(current_user: dict = Depends(require_any_internal_role())):
    return {"success": True, "data": REFERRAL_DESTINATIONS}
