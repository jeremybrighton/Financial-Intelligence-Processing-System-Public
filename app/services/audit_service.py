"""
FRC System — Audit Service
============================
Append-only audit logging. Every significant action writes a log entry.
Failures to log never raise — they're written to the app log only.
"""
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.core.database import audit_logs_col

log = logging.getLogger(__name__)


async def log_action(
    action: str,
    module: str,
    user_id: Optional[str] = None,
    user_email: Optional[str] = None,
    user_role: Optional[str] = None,
    target_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
) -> None:
    try:
        await audit_logs_col().insert_one({
            "user_id": user_id,
            "user_email": user_email,
            "user_role": user_role,
            "action": action,
            "module": module,
            "target_id": target_id,
            "details": details or {},
            "ip_address": ip_address,
            "timestamp": datetime.now(timezone.utc),
        })
    except Exception as e:
        log.error(f"Audit log write failed: {e} | action={action} | user={user_id}")


def extract_actor(user: dict) -> tuple:
    """Extract (user_id, email, role) from a user document."""
    return (str(user.get("_id", "")), user.get("email", ""), user.get("role", ""))
