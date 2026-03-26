"""FRC System — Audit Service (append-only logging)"""
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from backend.core.database import audit_logs_col
from backend.models.common import AuditActionType

log = logging.getLogger(__name__)

async def log_action(
    action_type: AuditActionType, module: str,
    actor_id: Optional[str] = None, actor_email: Optional[str] = None,
    actor_role: Optional[str] = None, target_entity: Optional[str] = None,
    target_id: Optional[str] = None, details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None, user_agent: Optional[str] = None,
    success: bool = True, error_message: Optional[str] = None,
) -> None:
    try:
        await audit_logs_col().insert_one({
            "timestamp": datetime.now(timezone.utc), "actor_id": actor_id,
            "actor_email": actor_email, "actor_role": actor_role,
            "action_type": action_type.value, "module": module,
            "target_entity": target_entity, "target_id": target_id,
            "details": details or {}, "ip_address": ip_address,
            "user_agent": user_agent, "success": success,
            "error_message": error_message, "created_at": datetime.now(timezone.utc),
        })
    except Exception as e:
        log.error(f"Failed to write audit log: {e} | action={action_type} | actor={actor_id}")

def extract_actor(user: dict) -> tuple:
    return (str(user.get("_id", "")), user.get("email", ""), user.get("role", ""))
