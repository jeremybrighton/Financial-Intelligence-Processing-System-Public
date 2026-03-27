"""
FRC System — Legal Rules Service
===================================
Manages the structured POCAMLA / POTA legal knowledge base.
Rules are stored as structured documents — no PDF reading at runtime.
"""
import logging
import math
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from bson import ObjectId

from app.core.database import legal_rules_col
from app.schemas.common import serialize_doc
from app.schemas.legal import (
    LegalRuleCreateRequest,
    LegalRuleDetailResponse,
    LegalRuleResponse,
    LegalRuleUpdateRequest,
)
from app.services.audit_service import extract_actor, log_action

log = logging.getLogger(__name__)


class ConflictError(Exception):
    pass


def _to_response(doc: dict) -> LegalRuleResponse:
    d = serialize_doc(doc)
    # Drop full_text and complex objects from list response
    d.pop("full_text", None)
    d.pop("trigger_condition", None)
    d.pop("system_use", None)
    return LegalRuleResponse(**d)


def _to_detail(doc: dict) -> LegalRuleDetailResponse:
    d = serialize_doc(doc)
    return LegalRuleDetailResponse(**d)


async def create_rule(body: LegalRuleCreateRequest, actor: dict) -> LegalRuleResponse:
    existing = await legal_rules_col().find_one({"rule_code": body.rule_code})
    if existing:
        raise ConflictError(f"Rule code '{body.rule_code}' already exists")

    now = datetime.now(timezone.utc)
    data = body.model_dump()
    # Serialize nested Pydantic objects
    if data.get("trigger_condition") and hasattr(data["trigger_condition"], "model_dump"):
        data["trigger_condition"] = data["trigger_condition"].model_dump()
    if data.get("system_use") and hasattr(data["system_use"], "model_dump"):
        data["system_use"] = data["system_use"].model_dump()

    doc = {**data, "is_active": True, "created_at": now, "updated_at": now}
    result = await legal_rules_col().insert_one(doc)
    doc["_id"] = result.inserted_id

    uid, uemail, urole = extract_actor(actor)
    await log_action(
        "legal_rule_created", "legal", uid, uemail, urole,
        str(result.inserted_id), {"rule_code": body.rule_code, "case_type": body.case_type},
    )
    return _to_response(doc)


async def list_rules(
    page: int = 1,
    page_size: int = 20,
    tag: Optional[str] = None,
    applicable_to: Optional[str] = None,
    rule_type: Optional[str] = None,
    case_type: Optional[str] = None,
    search: Optional[str] = None,
    active_only: bool = True,
) -> dict:
    query: Dict[str, Any] = {}
    if active_only:
        query["is_active"] = True
    if tag:
        query["tags"] = tag
    if applicable_to:
        query["applicable_to"] = applicable_to
    if rule_type:
        query["rule_type"] = rule_type
    if case_type:
        query["case_type"] = case_type
    if search:
        query["$or"] = [
            {"title": {"$regex": search, "$options": "i"}},
            {"summary": {"$regex": search, "$options": "i"}},
            {"rule_code": {"$regex": search, "$options": "i"}},
            {"act_name": {"$regex": search, "$options": "i"}},
        ]

    skip = (page - 1) * page_size
    total = await legal_rules_col().count_documents(query)
    proj = {"full_text": 0, "trigger_condition": 0, "system_use": 0}
    cursor = (
        legal_rules_col()
        .find(query, proj)
        .sort("rule_code", 1)
        .skip(skip)
        .limit(page_size)
    )
    items = [_to_response(d) async for d in cursor]
    return {
        "rules": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, math.ceil(total / page_size)),
    }


async def get_rule(rule_code: str) -> Optional[LegalRuleDetailResponse]:
    doc = await legal_rules_col().find_one({"rule_code": rule_code})
    return _to_detail(doc) if doc else None


async def get_rule_by_id(rule_id: str) -> Optional[LegalRuleDetailResponse]:
    try:
        doc = await legal_rules_col().find_one({"_id": ObjectId(rule_id)})
    except Exception:
        return None
    return _to_detail(doc) if doc else None


async def update_rule(
    rule_code: str, body: LegalRuleUpdateRequest, actor: dict
) -> Optional[LegalRuleResponse]:
    updates = {k: v for k, v in body.model_dump(exclude_none=True).items()}
    if not updates:
        doc = await legal_rules_col().find_one({"rule_code": rule_code}, {"full_text": 0, "trigger_condition": 0, "system_use": 0})
        return _to_response(doc) if doc else None

    updates["updated_at"] = datetime.now(timezone.utc)
    result = await legal_rules_col().update_one({"rule_code": rule_code}, {"$set": updates})
    if result.matched_count == 0:
        return None

    uid, uemail, urole = extract_actor(actor)
    await log_action("legal_rule_updated", "legal", uid, uemail, urole, rule_code)

    doc = await legal_rules_col().find_one({"rule_code": rule_code}, {"full_text": 0, "trigger_condition": 0, "system_use": 0})
    return _to_response(doc) if doc else None
