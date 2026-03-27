"""
Audit logs router — read-only.
GET /api/v1/audit-logs
GET /api/v1/audit-logs/{log_id}
"""
import logging
import math
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from app.core.database import audit_logs_col
from app.core.dependencies import require_roles, ROLE_FRC_ADMIN, ROLE_AUDIT_VIEWER

log = logging.getLogger(__name__)
router = APIRouter(prefix="/audit-logs", tags=["Audit Logs"])

_viewer = require_roles(ROLE_FRC_ADMIN, ROLE_AUDIT_VIEWER)


@router.get("", summary="Query audit logs")
async def list_audit_logs(
    page: int = 1,
    page_size: int = 50,
    module: str = None,
    action: str = None,
    user_id: str = None,
    target_id: str = None,
    current_user: dict = Depends(_viewer),
):
    query: dict = {}
    if module:
        query["module"] = module
    if action:
        query["action"] = action
    if user_id:
        query["user_id"] = user_id
    if target_id:
        query["target_id"] = target_id

    skip = (page - 1) * page_size
    total = await audit_logs_col().count_documents(query)
    cursor = audit_logs_col().find(query).sort("timestamp", -1).skip(skip).limit(page_size)
    items = []
    async for d in cursor:
        d["id"] = str(d.pop("_id"))
        items.append(d)

    return {
        "success": True,
        "data": {
            "logs": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": max(1, math.ceil(total / page_size)),
        },
    }


@router.get("/{log_id}", summary="Get a single audit log entry")
async def get_audit_log(
    log_id: str,
    current_user: dict = Depends(_viewer),
):
    try:
        doc = await audit_logs_col().find_one({"_id": ObjectId(log_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid log ID format")
    if not doc:
        raise HTTPException(status_code=404, detail=f"Log entry '{log_id}' not found")
    doc["id"] = str(doc.pop("_id"))
    return {"success": True, "data": doc}
