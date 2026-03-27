"""
FRC System — Legal Rules Service
===================================
Manages the structured legal knowledge base.
Derived from Acts and regulatory documents — not read from raw PDFs at runtime.
"""
import logging
import math
from datetime import datetime, timezone
from typing import Optional

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


async def create_rule(body: LegalRuleCreateRequest, actor: dict) -> LegalRuleResponse:
    existing = await legal_rules_col().find_one({"rule_code": body.rule_code})
    if existing:
        raise ConflictError(f"Rule code '{body.rule_code}' already exists")

    now = datetime.now(timezone.utc)
    doc = {
        **body.model_dump(),
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }
    result = await legal_rules_col().insert_one(doc)
    doc["_id"] = result.inserted_id

    uid, uemail, urole = extract_actor(actor)
    await log_action(
        "legal_rule_created", "legal", uid, uemail, urole,
        str(result.inserted_id), {"rule_code": body.rule_code},
    )
    d = serialize_doc(doc)
    return LegalRuleResponse(**{k: v for k, v in d.items() if k != "full_text"})


async def list_rules(
    page: int = 1,
    page_size: int = 20,
    tag: Optional[str] = None,
    applicable_to: Optional[str] = None,
    search: Optional[str] = None,
    active_only: bool = True,
) -> dict:
    query: dict = {}
    if active_only:
        query["is_active"] = True
    if tag:
        query["tags"] = tag
    if applicable_to:
        query["applicable_to"] = applicable_to
    if search:
        query["$or"] = [
            {"title": {"$regex": search, "$options": "i"}},
            {"summary": {"$regex": search, "$options": "i"}},
            {"rule_code": {"$regex": search, "$options": "i"}},
        ]

    skip = (page - 1) * page_size
    total = await legal_rules_col().count_documents(query)
    cursor = (
        legal_rules_col()
        .find(query, {"full_text": 0})
        .sort("rule_code", 1)
        .skip(skip)
        .limit(page_size)
    )
    items = [LegalRuleResponse(**serialize_doc(d)) async for d in cursor]
    return {
        "rules": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, math.ceil(total / page_size)),
    }


async def get_rule(rule_code: str) -> Optional[LegalRuleDetailResponse]:
    doc = await legal_rules_col().find_one({"rule_code": rule_code})
    return LegalRuleDetailResponse(**serialize_doc(doc)) if doc else None


async def get_rule_by_id(rule_id: str) -> Optional[LegalRuleDetailResponse]:
    try:
        doc = await legal_rules_col().find_one({"_id": ObjectId(rule_id)})
    except Exception:
        return None
    return LegalRuleDetailResponse(**serialize_doc(doc)) if doc else None


async def update_rule(
    rule_code: str, body: LegalRuleUpdateRequest, actor: dict
) -> Optional[LegalRuleResponse]:
    updates = {k: v for k, v in body.model_dump(exclude_none=True).items()}
    if not updates:
        return await get_rule(rule_code)
    updates["updated_at"] = datetime.now(timezone.utc)

    result = await legal_rules_col().update_one(
        {"rule_code": rule_code}, {"$set": updates}
    )
    if result.matched_count == 0:
        return None

    uid, uemail, urole = extract_actor(actor)
    await log_action("legal_rule_updated", "legal", uid, uemail, urole, rule_code)

    doc = await legal_rules_col().find_one({"rule_code": rule_code}, {"full_text": 0})
    return LegalRuleResponse(**serialize_doc(doc)) if doc else None


class ConflictError(Exception):
    pass
