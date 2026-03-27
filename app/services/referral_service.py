"""
FRC System — Referral Service
================================
Routes FRC cases to external agencies: DCI, KRA, CBK, EACC, NIS, etc.
"""
import logging
import math
from datetime import datetime, timezone
from typing import Optional

from app.core.database import cases_col, referrals_col
from app.schemas.common import serialize_doc
from app.schemas.referral import (
    ReferralCreateRequest,
    ReferralResponse,
    ReferralStatusUpdate,
)
from app.services.audit_service import extract_actor, log_action

log = logging.getLogger(__name__)


async def _next_referral_id() -> str:
    count = await referrals_col().count_documents({})
    year = datetime.now(timezone.utc).year
    return f"REF-{year}-{count + 1:05d}"


async def create_referral(body: ReferralCreateRequest, actor: dict) -> ReferralResponse:
    case = await cases_col().find_one({"frc_case_id": body.frc_case_id})
    if not case:
        raise ValueError(f"Case '{body.frc_case_id}' not found")

    referral_id = await _next_referral_id()
    now = datetime.now(timezone.utc)
    uid, uemail, urole = extract_actor(actor)

    doc = {
        "referral_id": referral_id,
        "frc_case_id": body.frc_case_id,
        "institution_id": case.get("institution_id", ""),
        "referred_to": body.referred_to,
        "reason": body.reason,
        "status": "pending",
        "notes": body.notes,
        "referred_by": uid,
        "sent_at": None,
        "acknowledged_at": None,
        "closed_at": None,
        "created_at": now,
        "updated_at": now,
    }
    result = await referrals_col().insert_one(doc)
    doc["_id"] = result.inserted_id

    # Update case status to referred
    await cases_col().update_one(
        {"frc_case_id": body.frc_case_id},
        {"$set": {
            "status": "referred",
            "referral_id": referral_id,
            "updated_at": now,
        }},
    )

    await log_action(
        "referral_created", "referrals", uid, uemail, urole,
        referral_id,
        {"frc_case_id": body.frc_case_id, "referred_to": body.referred_to},
    )
    return ReferralResponse(**serialize_doc(doc))


async def list_referrals(
    page: int = 1,
    page_size: int = 20,
    frc_case_id: Optional[str] = None,
    status: Optional[str] = None,
    referred_to: Optional[str] = None,
) -> dict:
    query: dict = {}
    if frc_case_id:
        query["frc_case_id"] = frc_case_id
    if status:
        query["status"] = status
    if referred_to:
        query["referred_to"] = referred_to

    skip = (page - 1) * page_size
    total = await referrals_col().count_documents(query)
    cursor = referrals_col().find(query).sort("created_at", -1).skip(skip).limit(page_size)
    items = [ReferralResponse(**serialize_doc(d)) async for d in cursor]
    return {
        "referrals": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, math.ceil(total / page_size)),
    }


async def get_referral(referral_id: str) -> Optional[ReferralResponse]:
    doc = await referrals_col().find_one({"referral_id": referral_id})
    return ReferralResponse(**serialize_doc(doc)) if doc else None


async def update_status(
    referral_id: str, body: ReferralStatusUpdate, actor: dict
) -> Optional[ReferralResponse]:
    doc = await referrals_col().find_one({"referral_id": referral_id})
    if not doc:
        return None

    now = datetime.now(timezone.utc)
    updates: dict = {"status": body.status, "updated_at": now}
    if body.notes:
        updates["notes"] = body.notes
    if body.status == "sent":
        updates["sent_at"] = now
    elif body.status == "acknowledged":
        updates["acknowledged_at"] = now
    elif body.status == "closed":
        updates["closed_at"] = now

    await referrals_col().update_one({"referral_id": referral_id}, {"$set": updates})

    uid, uemail, urole = extract_actor(actor)
    await log_action(
        "referral_status_updated", "referrals", uid, uemail, urole,
        referral_id, {"status": body.status},
    )

    updated = await referrals_col().find_one({"referral_id": referral_id})
    return ReferralResponse(**serialize_doc(updated))
