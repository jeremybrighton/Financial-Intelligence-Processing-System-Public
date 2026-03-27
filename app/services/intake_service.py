"""
FRC System — Intake Service
==============================
Processes incoming reportable case submissions from institution systems.
Creates immutable FRC case records and returns an acknowledgement.
"""
import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId

from app.core.config import settings
from app.core.database import cases_col, institutions_col
from app.schemas.common import serialize_doc
from app.schemas.intake import IntakeAcknowledgement, IntakeRequest
from app.services.audit_service import log_action

log = logging.getLogger(__name__)


async def _next_case_id() -> str:
    """Generate sequential FRC case ID: FRC-2026-00001."""
    count = await cases_col().count_documents({})
    return f"{settings.CASE_NUMBER_PREFIX}-{settings.CASE_NUMBER_YEAR}-{count + 1:05d}"


def _derive_priority(body: IntakeRequest) -> str:
    """Assign initial priority based on risk score or report type."""
    if body.risk_score is not None:
        if body.risk_score >= 0.85:
            return "high"
        if body.risk_score >= 0.60:
            return "medium"
    if body.report_type == "regulatory_threshold_report":
        if body.amount and body.amount >= 100_000:
            return "high"
    return "medium"


async def process_intake(
    body: IntakeRequest,
    institution: dict,
    submission_ip: Optional[str] = None,
) -> IntakeAcknowledgement:
    """
    Full intake pipeline:
      1. Build case document
      2. Generate FRC case ID
      3. Store in cases collection
      4. Write audit log
      5. Return acknowledgement
    """
    now = datetime.now(timezone.utc)
    institution_id = str(institution["_id"])

    try:
        frc_case_id = await _next_case_id()
    except Exception:
        frc_case_id = f"FRC-ERR-{uuid.uuid4().hex[:8].upper()}"

    priority = _derive_priority(body)

    case_doc = {
        "frc_case_id": frc_case_id,
        "institution_id": institution_id,
        "institution_code": institution.get("institution_code", ""),
        "external_report_id": body.external_report_id,
        "report_type": body.report_type,
        "status": "received",
        "priority": priority,
        "summary": None,
        "analyst_notes": None,
        "amount": body.amount,
        "currency": body.currency,
        "transaction_summary": body.transaction_summary,
        "triggering_rules": body.triggering_rules,
        "risk_score": body.risk_score,
        "narrative": body.narrative,
        "evidence_refs": [e.model_dump() for e in body.evidence_refs],
        "submission_metadata": {
            **(body.submission_metadata or {}),
            "received_at": now.isoformat(),
            "submission_ip": submission_ip,
            "event_timestamp": body.timestamp.isoformat() if body.timestamp else None,
        },
        "linked_report_id": None,
        "linked_legal_rule_ids": [],
        "referral_id": None,
        "created_at": now,
        "updated_at": now,
    }

    result = await cases_col().insert_one(case_doc)

    # Increment institution submission counter (async, non-blocking)
    asyncio.ensure_future(
        institutions_col().update_one(
            {"_id": institution["_id"]},
            {"$inc": {"submission_count": 1}},
        )
    )

    await log_action(
        action="case_received",
        module="intake",
        user_id=institution_id,
        user_email=institution.get("contact_email"),
        user_role="institution_api_client",
        target_id=frc_case_id,
        details={
            "report_type": body.report_type,
            "institution_code": institution.get("institution_code"),
            "priority": priority,
        },
        ip_address=submission_ip,
    )

    log.info(f"Intake complete: frc_case_id={frc_case_id} institution={institution.get('institution_code')}")

    return IntakeAcknowledgement(
        frc_case_id=frc_case_id,
        status="received",
        message=f"Case {frc_case_id} received successfully.",
        received_at=now,
    )
