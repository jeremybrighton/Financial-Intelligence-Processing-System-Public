"""
Audit log router — read-only for authorized roles.
GET /api/v1/audit/logs
"""
import logging
import math
from fastapi import APIRouter, Depends
from app.core.database import audit_logs_col
from app.core.dependencies import require_roles, ROLE_FRC_ADMIN, ROLE_AUDIT_VIEWER

log = logging.getLogger(__name__)
router = APIRouter(prefix="/audit", tags=["Audit Logs"])

_viewer = require_roles(ROLE_FRC_ADMIN, ROLE_AUDIT_VIEWER)


@router.get("/logs", summary="Query audit logs")
async def list_audit_logs(
    page: int = 1,
    page_size: int = 50,
    module: str = None,
    action: str = None,
    user_id: str = None,
    current_user: dict = Depends(_viewer),
):
    query: dict = {}
    if module:
        query["module"] = module
    if action:
        query["action"] = action
    if user_id:
        query["user_id"] = user_id

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
