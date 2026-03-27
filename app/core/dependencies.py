"""
FRC System — FastAPI Dependencies
=====================================
Reusable Depends() functions for auth and role guards.

Two completely separate auth tracks:
  1. JWT Bearer   — for human FRC dashboard users
  2. API Key      — for institution systems submitting cases (machine-to-machine)
"""
import logging
from typing import Optional

from bson import ObjectId
from fastapi import Depends, Header, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.database import institutions_col, users_col
from app.core.security import decode_token_safe, verify_api_key

log = logging.getLogger(__name__)
bearer_scheme = HTTPBearer(auto_error=False)

# ── Role constants ─────────────────────────────────────────────────────────────
ROLE_FRC_ADMIN       = "frc_admin"
ROLE_FRC_ANALYST     = "frc_analyst"
ROLE_INVESTIGATOR    = "investigator"
ROLE_AUDIT_VIEWER    = "audit_viewer"

ALL_INTERNAL_ROLES = {
    ROLE_FRC_ADMIN, ROLE_FRC_ANALYST,
    ROLE_INVESTIGATOR, ROLE_AUDIT_VIEWER,
}


def _unauthorized(detail: str = "Could not validate credentials") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def _forbidden(detail: str = "Insufficient permissions") -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


# ── Track 1: JWT user auth ────────────────────────────────────────────────────

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
) -> dict:
    """
    Resolve the authenticated FRC user from JWT Bearer token.
    Returns the MongoDB user document dict on success.
    """
    if not credentials:
        raise _unauthorized("No authentication token provided")

    payload = decode_token_safe(credentials.credentials)
    if not payload or payload.get("type") != "access":
        raise _unauthorized("Invalid or expired token")

    user_id = payload.get("sub")
    if not user_id:
        raise _unauthorized("Token missing subject")

    try:
        user = await users_col().find_one({"_id": ObjectId(user_id)})
    except Exception:
        raise _unauthorized("Invalid user ID in token")

    if not user:
        raise _unauthorized("User not found")
    if not user.get("is_active", True):
        raise HTTPException(status_code=403, detail="Account is deactivated")

    return user


# ── Role guards ───────────────────────────────────────────────────────────────

def require_roles(*roles: str):
    """Factory: returns a dependency that enforces one of the given roles."""
    async def checker(current_user: dict = Depends(get_current_user)) -> dict:
        if current_user.get("role") not in roles:
            raise _forbidden(f"Requires one of: {', '.join(roles)}")
        return current_user
    return checker


def require_admin():
    return require_roles(ROLE_FRC_ADMIN)

def require_admin_or_analyst():
    return require_roles(ROLE_FRC_ADMIN, ROLE_FRC_ANALYST)

def require_case_write():
    return require_roles(ROLE_FRC_ADMIN, ROLE_FRC_ANALYST, ROLE_INVESTIGATOR)

def require_any_internal_role():
    return require_roles(*ALL_INTERNAL_ROLES)


# ── Track 2: Institution API key auth ─────────────────────────────────────────

async def get_institution_from_api_key(
    x_institution_api_key: Optional[str] = Header(None, alias="X-Institution-API-Key"),
) -> dict:
    """
    Validates the X-Institution-API-Key header for machine-to-machine intake.
    Returns the institution MongoDB document on success.
    """
    if not x_institution_api_key:
        raise HTTPException(status_code=401, detail="Missing X-Institution-API-Key header")

    cursor = institutions_col().find({"is_active": True, "api_key_hash": {"$ne": None}})
    matched = None
    async for inst in cursor:
        if inst.get("api_key_hash") and verify_api_key(x_institution_api_key, inst["api_key_hash"]):
            matched = inst
            break

    if not matched:
        raise HTTPException(status_code=401, detail="Invalid or revoked API key")

    if matched.get("status") != "active":
        raise HTTPException(status_code=403, detail="Institution is not active")

    return matched
