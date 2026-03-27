"""
FRC System — Auth Service
===========================
Business logic for login, user creation, and user lookup.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId

from app.core.database import users_col
from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.core.config import settings
from app.models.user import ROLES
from app.schemas.auth import LoginRequest, TokenResponse, UserCreateRequest, UserResponse
from app.schemas.common import serialize_doc
from app.services.audit_service import log_action

log = logging.getLogger(__name__)


async def login(body: LoginRequest, ip_address: Optional[str] = None) -> TokenResponse:
    """Authenticate a user and return a JWT access token."""
    user = await users_col().find_one({"email": body.email.lower()})

    if not user or not verify_password(body.password, user.get("password_hash", "")):
        raise ValueError("Invalid email or password")

    if not user.get("is_active", True):
        raise PermissionError("Account is deactivated")

    user_id = str(user["_id"])
    token = create_access_token({"sub": user_id, "email": user["email"], "role": user["role"]})

    # Update last_login
    await users_col().update_one(
        {"_id": user["_id"]},
        {"$set": {"last_login": datetime.now(timezone.utc)}},
    )

    await log_action(
        action="user_login",
        module="auth",
        user_id=user_id,
        user_email=user["email"],
        user_role=user["role"],
        ip_address=ip_address,
    )

    return TokenResponse(
        access_token=token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user_id=user_id,
        full_name=user["full_name"],
        role=user["role"],
    )


async def create_user(body: UserCreateRequest, created_by: Optional[dict] = None) -> UserResponse:
    """Create a new FRC platform user."""
    if body.role not in ROLES:
        raise ValueError(f"Invalid role '{body.role}'. Valid roles: {ROLES}")

    existing = await users_col().find_one({"email": body.email.lower()})
    if existing:
        raise ConflictError("Email already registered")

    now = datetime.now(timezone.utc)
    doc = {
        "email": body.email.lower(),
        "full_name": body.full_name,
        "password_hash": hash_password(body.password),
        "role": body.role,
        "is_active": True,
        "last_login": None,
        "created_at": now,
        "updated_at": now,
    }
    result = await users_col().insert_one(doc)
    doc["_id"] = result.inserted_id

    if created_by:
        uid, uemail, urole = str(created_by.get("_id","")), created_by.get("email",""), created_by.get("role","")
        await log_action("user_created", "auth", uid, uemail, urole, str(result.inserted_id), {"email": body.email, "role": body.role})

    return UserResponse(**serialize_doc(doc))


async def get_user_by_id(user_id: str) -> Optional[UserResponse]:
    try:
        doc = await users_col().find_one({"_id": ObjectId(user_id)}, {"password_hash": 0})
    except Exception:
        return None
    return UserResponse(**serialize_doc(doc)) if doc else None


async def list_users(page: int = 1, page_size: int = 20) -> dict:
    skip = (page - 1) * page_size
    total = await users_col().count_documents({})
    cursor = users_col().find({}, {"password_hash": 0}).skip(skip).limit(page_size)
    users = [UserResponse(**serialize_doc(d)) async for d in cursor]
    import math
    return {
        "users": users,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, math.ceil(total / page_size)),
    }


async def deactivate_user(user_id: str, actor: dict) -> bool:
    try:
        result = await users_col().update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc)}},
        )
    except Exception:
        return False
    if result.matched_count:
        uid, uemail, urole = str(actor.get("_id","")), actor.get("email",""), actor.get("role","")
        await log_action("user_deactivated", "auth", uid, uemail, urole, user_id)
    return result.matched_count > 0


# Local import to avoid circular at module level
class ConflictError(Exception):
    pass
