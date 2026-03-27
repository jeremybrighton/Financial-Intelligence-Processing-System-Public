"""
FRC System — Case Management Service
=======================================
Business logic for FRC case lifecycle management.
"""
import logging
import math
from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId

from app.core.database import cases_col
from app.models.case import CASE_PRIORITIES, CASE_STATUSES
from app.schemas.case import CasePatchRequest, CaseResponse, CaseStatusUpdate
from app.schemas.common import serialize_doc
from app.services.audit_service import extract_actor, log_action

log = logging.getLogger(__name__)


# Valid status transitions — simple lifecycle guard
_TRANSITIONS: dict = {
    "received":         {"under_review", "closed"},
    "under_review":     {"report_generated", "referred", "closed"},
    "report_generated": {"referred", "closed"},
    "referred":         {"closed"},
    "closed":           set(),
}


def _to_response(doc: dict) -> CaseResponse:
    return CaseResponse(**serialize_doc(doc))


async def list_cases(
    page: int = 1,
    page_size: int = 20,
    status: Optional[str] = None,
    report_type: Optional[str] = None,
    priority: Optional[str] = None,
    institution_id: Optional[str] = None,
) -> dict:
    query: dict = {}
    if status:
        query["status"] = status
    if report_type:
        query["report_type"] = report_type
    if priority:
        query["priority"] = priority
    if institution_id:
        query["institution_id"] = institution_id

    skip = (page - 1) * page_size
    total = await cases_col().count_documents(query)
    cursor = cases_col().find(query).sort("created_at", -1).skip(skip).limit(page_size)
    items = [_to_response(d) async for d in cursor]

    return {
        "cases": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, math.ceil(total / page_size)),
    }


async def get_case(frc_case_id: str) -> Optional[CaseResponse]:
    doc = await cases_col().find_one({"frc_case_id": frc_case_id})
    return _to_response(doc) if doc else None


async def update_status(
    frc_case_id: str,
    body: CaseStatusUpdate,
    actor: dict,
) -> Optional[CaseResponse]:
    doc = await cases_col().find_one({"frc_case_id": frc_case_id})
    if not doc:
        return None

    current = doc.get("status", "received")
    allowed = _TRANSITIONS.get(current, set())

    if body.status not in allowed and body.status != current:
        raise ValueError(
            f"Cannot transition from '{current}' to '{body.status}'. "
            f"Allowed next: {sorted(allowed) or 'none (terminal)'}"
        )

    await cases_col().update_one(
        {"frc_case_id": frc_case_id},
        {"$set": {"status": body.status, "updated_at": datetime.now(timezone.utc)}},
    )

    uid, uemail, urole = extract_actor(actor)
    await log_action(
        "case_status_updated", "cases", uid, uemail, urole,
        frc_case_id,
        {"from": current, "to": body.status},
    )

    updated = await cases_col().find_one({"frc_case_id": frc_case_id})
    return _to_response(updated)


async def patch_case(
    frc_case_id: str,
    body: CasePatchRequest,
    actor: dict,
) -> Optional[CaseResponse]:
    updates = {k: v for k, v in body.model_dump(exclude_none=True).items()}
    if not updates:
        doc = await cases_col().find_one({"frc_case_id": frc_case_id})
        return _to_response(doc) if doc else None

    if "priority" in updates and updates["priority"] not in CASE_PRIORITIES:
        raise ValueError(f"Invalid priority: {updates['priority']}")

    updates["updated_at"] = datetime.now(timezone.utc)

    result = await cases_col().update_one(
        {"frc_case_id": frc_case_id},
        {"$set": updates},
    )
    if result.matched_count == 0:
        return None

    uid, uemail, urole = extract_actor(actor)
    await log_action(
        "case_updated", "cases", uid, uemail, urole,
        frc_case_id, {"fields": list(updates.keys())},
    )

    updated = await cases_col().find_one({"frc_case_id": frc_case_id})
    return _to_response(updated)
