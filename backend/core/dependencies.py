"""
FRC System — FastAPI Dependency Injection
JWT user resolution and role guards.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from fastapi import Depends, Header, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.core.database import api_keys_col, institutions_col, users_col
from backend.core.security import decode_token_safe, verify_api_key

log = logging.getLogger(__name__)
bearer_scheme = HTTPBearer(auto_error=False)

ROLE_FRC_ADMIN        = "frc_admin"
ROLE_FRC_SUPERVISOR   = "frc_supervisor"
ROLE_FRC_ANALYST      = "frc_analyst"
ROLE_FRC_INVESTIGATOR = "frc_investigator"
ROLE_FRC_AUDITOR      = "frc_auditor"

ALL_FRC_ROLES = {ROLE_FRC_ADMIN, ROLE_FRC_SUPERVISOR, ROLE_FRC_ANALYST, ROLE_FRC_INVESTIGATOR, ROLE_FRC_AUDITOR}


def _creds_exc(detail="Could not validate credentials"):
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail, headers={"WWW-Authenticate": "Bearer"})


async def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme)) -> dict:
    if not credentials:
        raise _creds_exc("No authentication token provided")
    payload = decode_token_safe(credentials.credentials)
    if not payload or payload.get("type") != "access":
        raise _creds_exc("Invalid or expired token")
    user_id = payload.get("sub")
    if not user_id:
        raise _creds_exc("Token missing subject")
    try:
        user = await users_col().find_one({"_id": ObjectId(user_id)})
    except Exception:
        raise _creds_exc("Invalid user identifier")
    if not user:
        raise _creds_exc("User not found")
    if not user.get("is_active", True):
        raise HTTPException(status_code=403, detail="Account is deactivated")
    return user


def require_roles(*roles: str):
    async def checker(current_user: dict = Depends(get_current_user)) -> dict:
        if current_user.get("role") not in roles:
            raise HTTPException(status_code=403, detail=f"Requires one of: {', '.join(roles)}")
        return current_user
    return checker


def require_admin():                return require_roles(ROLE_FRC_ADMIN)
def require_admin_or_supervisor():  return require_roles(ROLE_FRC_ADMIN, ROLE_FRC_SUPERVISOR)
def require_case_write():           return require_roles(ROLE_FRC_ADMIN, ROLE_FRC_SUPERVISOR, ROLE_FRC_ANALYST, ROLE_FRC_INVESTIGATOR)
def require_report_write():         return require_roles(ROLE_FRC_ADMIN, ROLE_FRC_SUPERVISOR, ROLE_FRC_ANALYST)
def require_any_frc_role():         return require_roles(*ALL_FRC_ROLES)


async def get_institution_from_api_key(
    x_institution_api_key: Optional[str] = Header(None, alias="X-Institution-API-Key"),
) -> dict:
    if not x_institution_api_key:
        raise HTTPException(status_code=401, detail="Missing X-Institution-API-Key header")
    cursor = api_keys_col().find({"is_active": True})
    matched = None
    async for key_doc in cursor:
        if verify_api_key(x_institution_api_key, key_doc["key_hash"]):
            matched = key_doc
            break
    if not matched:
        raise HTTPException(status_code=401, detail="Invalid or revoked API key")
    expires_at = matched.get("expires_at")
    if expires_at and datetime.now(timezone.utc) > expires_at:
        raise HTTPException(status_code=401, detail="API key has expired")
    institution = await institutions_col().find_one({"_id": matched["institution_id"] if isinstance(matched["institution_id"], ObjectId) else ObjectId(matched["institution_id"]), "is_active": True})
    if not institution:
        raise HTTPException(status_code=403, detail="Institution is not active")
    import asyncio
    asyncio.ensure_future(api_keys_col().update_one({"_id": matched["_id"]}, {"$set": {"last_used_at": datetime.now(timezone.utc)}}))
    return institution
