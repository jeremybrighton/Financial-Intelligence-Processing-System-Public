"""FRC System — Intake Service (automatic, policy-driven case creation)"""
import asyncio, logging, uuid
from datetime import datetime, timezone
from typing import Optional
from bson import ObjectId
from backend.core.config import settings
from backend.core.database import case_submissions_col, case_timeline_col, frc_cases_col, institutions_col
from backend.models.common import AuditActionType, CasePriority, CaseStatus, SubmissionStatus, SubmissionType
from backend.models.intake import IntakeAcknowledgement, SubmissionPayload
from backend.services.audit_service import log_action

log = logging.getLogger(__name__)

async def _next_case_number() -> str:
    count = await frc_cases_col().count_documents({})
    return f"{settings.CASE_NUMBER_PREFIX}-{settings.CASE_NUMBER_YEAR}-{count + 1:05d}"

def _derive_priority(payload: SubmissionPayload) -> CasePriority:
    tx = payload.transaction
    if payload.submission_type == SubmissionType.SUSPICIOUS_ACTIVITY_REPORT and tx.ml_score is not None:
        if tx.ml_score >= 0.90: return CasePriority.CRITICAL
        if tx.ml_score >= 0.75: return CasePriority.HIGH
        if tx.ml_score >= 0.50: return CasePriority.MEDIUM
    if tx.amount_usd_equivalent and tx.amount_usd_equivalent >= 100_000: return CasePriority.HIGH
    return CasePriority.MEDIUM

async def process_submission(payload: SubmissionPayload, institution: dict, submission_ip: Optional[str] = None) -> IntakeAcknowledgement:
    from backend.core.exceptions import IntakeError
    now = datetime.now(timezone.utc)
    institution_id = str(institution["_id"]); institution_code = institution["institution_code"]

    submission_doc = {
        "institution_id": institution_id, "institution_code": institution_code,
        "received_at": now, "payload": payload.model_dump(mode="json"),
        "submission_type": payload.submission_type.value, "status": SubmissionStatus.RECEIVED.value,
        "triggered_rules": payload.triggered_rules, "transaction_ref": payload.transaction.transaction_ref,
        "source_batch_id": payload.source_batch_id, "source_system": payload.source_system,
        "submission_ip": submission_ip, "frc_case_id": None, "created_at": now, "updated_at": now,
    }
    try:
        result = await case_submissions_col().insert_one(submission_doc)
        submission_id = str(result.inserted_id)
    except Exception as e:
        log.error(f"Failed to store submission: {e}"); raise IntakeError("Failed to store submission")

    try:
        case_number = await _next_case_number()
    except Exception:
        case_number = f"FRC-ERR-{uuid.uuid4().hex[:8].upper()}"

    priority = _derive_priority(payload); tx = payload.transaction
    case_doc = {
        "case_number": case_number, "submission_id": submission_id,
        "institution_id": institution_id, "institution_code": institution_code,
        "status": CaseStatus.RECEIVED.value, "submission_type": payload.submission_type.value,
        "priority": priority.value, "assigned_to": None, "assigned_at": None, "closed_at": None,
        "transaction_ref": tx.transaction_ref, "transaction_date": tx.transaction_date,
        "amount": tx.amount, "currency": tx.currency, "amount_usd_equivalent": tx.amount_usd_equivalent,
        "subject_name": tx.sender_name, "subject_account": tx.sender_account,
        "recipient_name": tx.recipient_name, "recipient_account": tx.recipient_account,
        "ml_score": tx.ml_score, "triggered_rules": payload.triggered_rules,
        "case_type": None, "summary": None, "tags": [], "created_at": now, "updated_at": now,
    }
    try:
        case_result = await frc_cases_col().insert_one(case_doc)
        case_id = str(case_result.inserted_id)
    except Exception as e:
        log.error(f"Failed to create FRC case: {e}"); raise IntakeError("Failed to create FRC case")

    await case_submissions_col().update_one({"_id": ObjectId(submission_id)}, {"$set": {"frc_case_id": case_id, "status": SubmissionStatus.ACCEPTED.value}})
    await case_timeline_col().insert_one({
        "case_id": case_id, "timestamp": now, "actor_id": None, "actor_name": "System",
        "event_type": "case_created", "from_status": None, "to_status": CaseStatus.RECEIVED.value,
        "note": f"Case auto-created from {payload.submission_type.value} by {institution_code}. Rules: {', '.join(payload.triggered_rules)}",
        "created_at": now,
    })
    asyncio.ensure_future(institutions_col().update_one({"_id": institution["_id"]}, {"$inc": {"submitted_case_count": 1}}))
    await log_action(
        action_type=AuditActionType.SUBMISSION_RECEIVED, module="intake",
        actor_id=institution_id, actor_email=institution.get("contact_email"), actor_role="institution_api",
        target_entity="frc_cases", target_id=case_id,
        details={"submission_id": submission_id, "case_number": case_number, "submission_type": payload.submission_type.value, "triggered_rules": payload.triggered_rules},
        ip_address=submission_ip,
    )
    log.info(f"Intake: submission_id={submission_id} case_id={case_id} case_number={case_number}")
    return IntakeAcknowledgement(
        success=True, frc_case_id=case_id, submission_id=submission_id,
        submission_type=payload.submission_type, status=SubmissionStatus.ACCEPTED, received_at=now,
        message=f"FRC case {case_number} created. Type: {payload.submission_type.value}",
    )
