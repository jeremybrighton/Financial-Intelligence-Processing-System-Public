"""FRC System — Case Management Service"""
import logging, math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from bson import ObjectId
from backend.core.database import case_evidence_col, case_notes_col, case_reports_col, case_timeline_col, frc_cases_col, referrals_col, users_col
from backend.models.common import AuditActionType, CasePriority, CaseStatus
from backend.services.audit_service import extract_actor, log_action

log = logging.getLogger(__name__)

STATUS_TRANSITIONS = {
    CaseStatus.RECEIVED: {CaseStatus.ACKNOWLEDGED, CaseStatus.WITHDRAWN},
    CaseStatus.ACKNOWLEDGED: {CaseStatus.UNDER_REVIEW, CaseStatus.WITHDRAWN},
    CaseStatus.UNDER_REVIEW: {CaseStatus.ON_HOLD, CaseStatus.INVESTIGATION_COMPLETE, CaseStatus.WITHDRAWN},
    CaseStatus.ON_HOLD: {CaseStatus.UNDER_REVIEW, CaseStatus.WITHDRAWN},
    CaseStatus.INVESTIGATION_COMPLETE: {CaseStatus.REPORT_DRAFTED, CaseStatus.UNDER_REVIEW},
    CaseStatus.REPORT_DRAFTED: {CaseStatus.REPORT_UNDER_REVIEW},
    CaseStatus.REPORT_UNDER_REVIEW: {CaseStatus.REPORT_FINALISED, CaseStatus.REPORT_REVISION_REQUIRED},
    CaseStatus.REPORT_REVISION_REQUIRED: {CaseStatus.REPORT_DRAFTED},
    CaseStatus.REPORT_FINALISED: {CaseStatus.REFERRED},
    CaseStatus.REFERRED: {CaseStatus.REFERRAL_ACKNOWLEDGED, CaseStatus.RESOLVED},
    CaseStatus.REFERRAL_ACKNOWLEDGED: {CaseStatus.RESOLVED},
    CaseStatus.RESOLVED: {CaseStatus.ARCHIVED},
    CaseStatus.ARCHIVED: set(), CaseStatus.WITHDRAWN: set(),
}

def _s(doc):
    if doc and "_id" in doc: doc["_id"] = str(doc["_id"])
    return doc

def _pag(total, page, page_size):
    return {"total": total, "page": page, "page_size": page_size, "total_pages": max(1, math.ceil(total/page_size))}

async def get_case_by_id(case_id: str):
    try:
        doc = await frc_cases_col().find_one({"_id": ObjectId(case_id)})
        return _s(doc) if doc else None
    except Exception: return None

async def list_cases(filters: dict, page=1, page_size=20):
    query: Dict[str, Any] = {}
    if filters.get("status"): query["status"] = filters["status"]
    if filters.get("priority"): query["priority"] = filters["priority"]
    if filters.get("submission_type"): query["submission_type"] = filters["submission_type"]
    if filters.get("institution_id"): query["institution_id"] = filters["institution_id"]
    if filters.get("assigned_to"): query["assigned_to"] = filters["assigned_to"]
    if filters.get("search"):
        t = filters["search"]
        query["$or"] = [{"case_number":{"$regex":t,"$options":"i"}},{"transaction_ref":{"$regex":t,"$options":"i"}},{"subject_name":{"$regex":t,"$options":"i"}}]
    total = await frc_cases_col().count_documents(query)
    cursor = frc_cases_col().find(query).sort("created_at", -1).skip((page-1)*page_size).limit(page_size)
    return {"cases": [_s(d) async for d in cursor], **_pag(total, page, page_size)}

async def get_case_detail(case_id: str):
    case = await get_case_by_id(case_id)
    if not case: return None
    timeline = [_s(d) async for d in case_timeline_col().find({"case_id": case_id}).sort("timestamp",-1).limit(20)]
    notes = [_s(d) async for d in case_notes_col().find({"case_id": case_id}).sort("created_at",-1).limit(5)]
    evidence_count = await case_evidence_col().count_documents({"case_id": case_id})
    reports_count = await case_reports_col().count_documents({"case_id": case_id})
    referrals_count = await referrals_col().count_documents({"case_id": case_id})
    return {**case, "timeline": timeline, "recent_notes": notes, "evidence_count": evidence_count, "reports_count": reports_count, "referrals_count": referrals_count}

async def update_case_status(case_id, new_status, actor, note=None, is_admin=False):
    from backend.core.exceptions import FRCException
    case = await get_case_by_id(case_id)
    if not case: raise FRCException("Case not found", 404)
    current = CaseStatus(case["status"])
    allowed = STATUS_TRANSITIONS.get(current, set())
    if is_admin and current in {CaseStatus.RESOLVED, CaseStatus.ARCHIVED}: allowed = allowed | {CaseStatus.UNDER_REVIEW}
    if new_status not in allowed: raise FRCException(f"Transition '{current.value}'→'{new_status.value}' not allowed", 422)
    now = datetime.now(timezone.utc)
    updates = {"status": new_status.value, "updated_at": now}
    if new_status in {CaseStatus.RESOLVED, CaseStatus.ARCHIVED, CaseStatus.WITHDRAWN}: updates["closed_at"] = now
    await frc_cases_col().update_one({"_id": ObjectId(case_id)}, {"$set": updates})
    actor_id, actor_email, actor_role = extract_actor(actor)
    await case_timeline_col().insert_one({"case_id": case_id, "timestamp": now, "actor_id": actor_id, "actor_name": actor.get("full_name", actor_email), "event_type": "status_change", "from_status": current.value, "to_status": new_status.value, "note": note, "created_at": now})
    await log_action(action_type=AuditActionType.CASE_STATUS_CHANGED, module="case", actor_id=actor_id, actor_email=actor_email, actor_role=actor_role, target_entity="frc_cases", target_id=case_id, details={"case_number": case.get("case_number"), "from_status": current.value, "to_status": new_status.value})
    return await get_case_by_id(case_id)

async def assign_case(case_id, user_id, actor, note=None):
    from backend.core.exceptions import NotFoundError
    case = await get_case_by_id(case_id)
    if not case: raise NotFoundError("Case", case_id)
    user = await users_col().find_one({"_id": ObjectId(user_id)})
    if not user: raise NotFoundError("User", user_id)
    now = datetime.now(timezone.utc)
    await frc_cases_col().update_one({"_id": ObjectId(case_id)}, {"$set": {"assigned_to": user_id, "assigned_at": now, "updated_at": now}})
    actor_id, actor_email, actor_role = extract_actor(actor)
    await case_timeline_col().insert_one({"case_id": case_id, "timestamp": now, "actor_id": actor_id, "actor_name": actor.get("full_name", actor_email), "event_type": "case_assigned", "from_status": None, "to_status": None, "note": note or f"Assigned to {user.get('full_name', user_id)}", "created_at": now})
    await log_action(action_type=AuditActionType.CASE_ASSIGNED, module="case", actor_id=actor_id, actor_email=actor_email, actor_role=actor_role, target_entity="frc_cases", target_id=case_id, details={"assigned_to": user_id})
    return await get_case_by_id(case_id)

async def add_note(case_id, content, actor, is_internal=True):
    from backend.core.exceptions import NotFoundError
    if not await get_case_by_id(case_id): raise NotFoundError("Case", case_id)
    actor_id, actor_email, actor_role = extract_actor(actor)
    now = datetime.now(timezone.utc)
    doc = {"case_id": case_id, "author_id": actor_id, "author_name": actor.get("full_name", actor_email), "content": content, "is_internal": is_internal, "created_at": now, "updated_at": now}
    result = await case_notes_col().insert_one(doc); doc["_id"] = str(result.inserted_id)
    await log_action(action_type=AuditActionType.CASE_NOTE_ADDED, module="case", actor_id=actor_id, actor_email=actor_email, actor_role=actor_role, target_entity="frc_cases", target_id=case_id)
    return doc

async def list_notes(case_id, page=1, page_size=20):
    skip = (page-1)*page_size; total = await case_notes_col().count_documents({"case_id": case_id})
    cursor = case_notes_col().find({"case_id": case_id}).sort("created_at",-1).skip(skip).limit(page_size)
    return {"notes": [_s(d) async for d in cursor], **_pag(total, page, page_size)}

async def add_evidence(case_id, evidence_data, actor):
    from backend.core.exceptions import NotFoundError
    if not await get_case_by_id(case_id): raise NotFoundError("Case", case_id)
    actor_id, actor_email, actor_role = extract_actor(actor)
    now = datetime.now(timezone.utc)
    doc = {"case_id": case_id, "added_by": actor_id, "added_by_name": actor.get("full_name", actor_email), "created_at": now, "updated_at": now, **evidence_data}
    result = await case_evidence_col().insert_one(doc); doc["_id"] = str(result.inserted_id)
    await log_action(action_type=AuditActionType.CASE_EVIDENCE_ADDED, module="case", actor_id=actor_id, actor_email=actor_email, actor_role=actor_role, target_entity="frc_cases", target_id=case_id)
    return doc

async def list_evidence(case_id):
    return [_s(d) async for d in case_evidence_col().find({"case_id": case_id}).sort("created_at",-1)]
