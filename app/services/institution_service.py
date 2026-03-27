"""
FRC System — Institution Service
===================================
Business logic for institution registry management.
"""
import logging
import math
from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId

from app.core.database import institutions_col
from app.core.security import generate_api_key, get_key_suffix, hash_api_key
from app.models.institution import INSTITUTION_STATUSES, INSTITUTION_TYPES
from app.schemas.common import serialize_doc
from app.schemas.institution import (
    ApiKeyResponse,
    InstitutionCreateRequest,
    InstitutionResponse,
    InstitutionStatusUpdate,
    InstitutionUpdateRequest,
)
from app.services.audit_service import extract_actor, log_action

log = logging.getLogger(__name__)


def _to_response(doc: dict) -> InstitutionResponse:
    return InstitutionResponse(**serialize_doc(doc))


async def create_institution(body: InstitutionCreateRequest, actor: dict) -> InstitutionResponse:
    if body.institution_type not in INSTITUTION_TYPES:
        raise ValueError(f"Invalid institution_type: {body.institution_type}")
    if body.status not in INSTITUTION_STATUSES:
        raise ValueError(f"Invalid status: {body.status}")

    existing = await institutions_col().find_one({"institution_code": body.institution_code})
    if existing:
        raise ConflictError(f"Institution code '{body.institution_code}' already exists")

    now = datetime.now(timezone.utc)
    doc = {
        "institution_code": body.institution_code,
        "institution_name": body.institution_name,
        "institution_type": body.institution_type,
        "supervisory_body": body.supervisory_body,
        "contact_email": body.contact_email.lower(),
        "status": body.status,
        "is_active": body.status == "active",
        "api_key_hash": None,
        "api_key_suffix": None,
        "created_at": now,
        "updated_at": now,
    }
    result = await institutions_col().insert_one(doc)
    doc["_id"] = result.inserted_id

    uid, uemail, urole = extract_actor(actor)
    await log_action(
        "institution_created", "institutions", uid, uemail, urole,
        str(result.inserted_id),
        {"institution_code": body.institution_code, "name": body.institution_name},
    )
    return _to_response(doc)


async def list_institutions(
    page: int = 1,
    page_size: int = 20,
    status: Optional[str] = None,
    institution_type: Optional[str] = None,
) -> dict:
    query = {}
    if status:
        query["status"] = status
    if institution_type:
        query["institution_type"] = institution_type

    skip = (page - 1) * page_size
    total = await institutions_col().count_documents(query)
    cursor = institutions_col().find(query).sort("created_at", -1).skip(skip).limit(page_size)
    items = [_to_response(d) async for d in cursor]
    return {
        "institutions": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, math.ceil(total / page_size)),
    }


async def get_institution_by_id(institution_id: str) -> Optional[InstitutionResponse]:
    try:
        doc = await institutions_col().find_one({"_id": ObjectId(institution_id)})
    except Exception:
        return None
    return _to_response(doc) if doc else None


async def get_institution_by_code(code: str) -> Optional[dict]:
    return await institutions_col().find_one({"institution_code": code})


async def update_institution(
    institution_id: str,
    body: InstitutionUpdateRequest,
    actor: dict,
) -> Optional[InstitutionResponse]:
    updates = {k: v for k, v in body.model_dump(exclude_none=True).items()}
    if "contact_email" in updates:
        updates["contact_email"] = updates["contact_email"].lower()
    if "institution_type" in updates and updates["institution_type"] not in INSTITUTION_TYPES:
        raise ValueError(f"Invalid institution_type: {updates['institution_type']}")
    updates["updated_at"] = datetime.now(timezone.utc)

    try:
        result = await institutions_col().update_one(
            {"_id": ObjectId(institution_id)}, {"$set": updates}
        )
    except Exception:
        return None

    if result.matched_count == 0:
        return None

    uid, uemail, urole = extract_actor(actor)
    await log_action("institution_updated", "institutions", uid, uemail, urole, institution_id)
    return await get_institution_by_id(institution_id)


async def update_status(
    institution_id: str,
    body: InstitutionStatusUpdate,
    actor: dict,
) -> Optional[InstitutionResponse]:
    try:
        result = await institutions_col().update_one(
            {"_id": ObjectId(institution_id)},
            {"$set": {
                "status": body.status,
                "is_active": body.status == "active",
                "updated_at": datetime.now(timezone.utc),
            }},
        )
    except Exception:
        return None

    if result.matched_count == 0:
        return None

    uid, uemail, urole = extract_actor(actor)
    await log_action(
        "institution_status_updated", "institutions", uid, uemail, urole,
        institution_id, {"status": body.status},
    )
    return await get_institution_by_id(institution_id)


async def generate_institution_api_key(institution_id: str, actor: dict) -> ApiKeyResponse:
    """
    Generate and store a new API key for an institution.
    The raw key is returned once. Only the hash is stored.
    """
    try:
        inst = await institutions_col().find_one({"_id": ObjectId(institution_id)})
    except Exception:
        raise ValueError("Invalid institution ID")

    if not inst:
        raise ValueError("Institution not found")
    if inst.get("status") != "active":
        raise ValueError("Cannot issue API key for non-active institution")

    raw_key = generate_api_key()
    suffix = get_key_suffix(raw_key)

    await institutions_col().update_one(
        {"_id": ObjectId(institution_id)},
        {"$set": {
            "api_key_hash": hash_api_key(raw_key),
            "api_key_suffix": suffix,
            "updated_at": datetime.now(timezone.utc),
        }},
    )

    uid, uemail, urole = extract_actor(actor)
    await log_action(
        "api_key_generated", "institutions", uid, uemail, urole,
        institution_id, {"suffix": suffix},
    )

    return ApiKeyResponse(api_key=raw_key, api_key_suffix=suffix)


class ConflictError(Exception):
    pass
