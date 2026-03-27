"""
FRC System — Report Service
==============================
Manages FRC-generated case reports (STR, CTR, SAR etc.).
Reports are linked to cases and may reference legal rules.
"""
import logging
import math
import uuid
from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId

from app.core.database import cases_col, reports_col
from app.schemas.common import serialize_doc
from app.schemas.report import (
    ReportCreateRequest,
    ReportResponse,
    ReportStatusUpdate,
    ReportUpdateRequest,
)
from app.services.audit_service import extract_actor, log_action

log = logging.getLogger(__name__)


async def _next_report_id() -> str:
    count = await reports_col().count_documents({})
    year = datetime.now(timezone.utc).year
    return f"RPT-{year}-{count + 1:05d}"


async def create_report(body: ReportCreateRequest, actor: dict) -> ReportResponse:
    # Verify case exists
    case = await cases_col().find_one({"frc_case_id": body.frc_case_id})
    if not case:
        raise ValueError(f"Case '{body.frc_case_id}' not found")

    report_id = await _next_report_id()
    now = datetime.now(timezone.utc)
    uid, uemail, urole = extract_actor(actor)

    doc = {
        "report_id": report_id,
        "frc_case_id": body.frc_case_id,
        "institution_id": case.get("institution_id", ""),
        "report_type": body.report_type,
        "status": "draft",
        "title": body.title,
        "content": body.content,
        "prepared_by": uid,
        "reviewed_by": None,
        "finalised_at": None,
        "legal_rule_ids": body.legal_rule_ids,
        "created_at": now,
        "updated_at": now,
    }
    result = await reports_col().insert_one(doc)
    doc["_id"] = result.inserted_id

    await log_action(
        "report_created", "reports", uid, uemail, urole,
        report_id, {"frc_case_id": body.frc_case_id, "report_type": body.report_type},
    )
    return ReportResponse(**serialize_doc(doc))


async def list_reports(
    page: int = 1,
    page_size: int = 20,
    frc_case_id: Optional[str] = None,
    status: Optional[str] = None,
) -> dict:
    query: dict = {}
    if frc_case_id:
        query["frc_case_id"] = frc_case_id
    if status:
        query["status"] = status

    skip = (page - 1) * page_size
    total = await reports_col().count_documents(query)
    cursor = reports_col().find(query).sort("created_at", -1).skip(skip).limit(page_size)
    items = [ReportResponse(**serialize_doc(d)) async for d in cursor]
    return {
        "reports": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, math.ceil(total / page_size)),
    }


async def get_report(report_id: str) -> Optional[ReportResponse]:
    doc = await reports_col().find_one({"report_id": report_id})
    return ReportResponse(**serialize_doc(doc)) if doc else None


async def update_report(
    report_id: str, body: ReportUpdateRequest, actor: dict
) -> Optional[ReportResponse]:
    doc = await reports_col().find_one({"report_id": report_id})
    if not doc:
        return None
    if doc.get("status") == "finalised":
        raise ValueError("Cannot edit a finalised report")

    updates = {k: v for k, v in body.model_dump(exclude_none=True).items()}
    updates["updated_at"] = datetime.now(timezone.utc)

    await reports_col().update_one({"report_id": report_id}, {"$set": updates})

    uid, uemail, urole = extract_actor(actor)
    await log_action("report_updated", "reports", uid, uemail, urole, report_id)

    updated = await reports_col().find_one({"report_id": report_id})
    return ReportResponse(**serialize_doc(updated))


async def update_status(
    report_id: str, body: ReportStatusUpdate, actor: dict
) -> Optional[ReportResponse]:
    doc = await reports_col().find_one({"report_id": report_id})
    if not doc:
        return None

    updates: dict = {"status": body.status, "updated_at": datetime.now(timezone.utc)}
    if body.status == "finalised":
        uid, _, _ = extract_actor(actor)
        updates["reviewed_by"] = uid
        updates["finalised_at"] = datetime.now(timezone.utc)
        # Sync case status
        await cases_col().update_one(
            {"frc_case_id": doc["frc_case_id"]},
            {"$set": {
                "status": "report_generated",
                "linked_report_id": report_id,
                "updated_at": datetime.now(timezone.utc),
            }},
        )

    await reports_col().update_one({"report_id": report_id}, {"$set": updates})

    uid, uemail, urole = extract_actor(actor)
    await log_action(
        "report_status_updated", "reports", uid, uemail, urole,
        report_id, {"status": body.status},
    )

    updated = await reports_col().find_one({"report_id": report_id})
    return ReportResponse(**serialize_doc(updated))
