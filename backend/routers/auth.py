"""FRC System — Auth Router"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request
from backend.core.database import refresh_tokens_col, users_col
from backend.core.dependencies import get_current_user
from backend.core.security import create_access_token, create_refresh_token, decode_token_safe, generate_otp, hash_password, hash_token, send_otp_email, verify_password
from backend.core.config import settings
from backend.models.common import AuditActionType
from backend.models.user import LoginRequest, PasswordChangeRequest, PasswordResetConfirmRequest, PasswordResetRequest, RefreshTokenRequest
from backend.services.audit_service import extract_actor, log_action

log = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])

def _u(user):
    return {"id": str(user["_id"]), "_id": str(user["_id"]), "email": user["email"], "full_name": user["full_name"], "role": user["role"], "is_active": user.get("is_active", True), "last_login": user.get("last_login"), "created_at": user.get("created_at")}

@router.post("/login")
async def login(body: LoginRequest, request: Request):
    user = await users_col().find_one({"email": body.email.lower()})
    if not user or not verify_password(body.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.get("is_active", True): raise HTTPException(status_code=403, detail="Account is deactivated")
    user_id = str(user["_id"]); token_data = {"sub": user_id, "email": user["email"], "role": user["role"]}
    access_token = create_access_token(token_data); refresh_token = create_refresh_token(token_data)
    await refresh_tokens_col().insert_one({"token_hash": hash_token(refresh_token), "user_id": user_id, "created_at": datetime.now(timezone.utc), "expires_at": datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)})
    await users_col().update_one({"_id": user["_id"]}, {"$set": {"last_login": datetime.now(timezone.utc)}})
    await log_action(action_type=AuditActionType.USER_LOGIN, module="auth", actor_id=user_id, actor_email=user["email"], actor_role=user["role"], ip_address=request.client.host if request.client else None)
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer", "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES*60, "user": _u(user)}

@router.post("/refresh")
async def refresh_token(body: RefreshTokenRequest):
    payload = decode_token_safe(body.refresh_token)
    if not payload or payload.get("type") != "refresh": raise HTTPException(status_code=401, detail="Invalid refresh token")
    stored = await refresh_tokens_col().find_one({"token_hash": hash_token(body.refresh_token)})
    if not stored: raise HTTPException(status_code=401, detail="Refresh token not found")
    user = await users_col().find_one({"_id": ObjectId(payload["sub"])})
    if not user or not user.get("is_active", True): raise HTTPException(status_code=401, detail="User not found")
    await refresh_tokens_col().delete_one({"token_hash": hash_token(body.refresh_token)})
    token_data = {"sub": str(user["_id"]), "email": user["email"], "role": user["role"]}
    new_access = create_access_token(token_data); new_refresh = create_refresh_token(token_data)
    await refresh_tokens_col().insert_one({"token_hash": hash_token(new_refresh), "user_id": str(user["_id"]), "created_at": datetime.now(timezone.utc), "expires_at": datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)})
    return {"access_token": new_access, "refresh_token": new_refresh, "token_type": "bearer", "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES*60}

@router.post("/logout")
async def logout(body: RefreshTokenRequest, current_user: dict = Depends(get_current_user)):
    await refresh_tokens_col().delete_one({"token_hash": hash_token(body.refresh_token)})
    actor_id, actor_email, actor_role = extract_actor(current_user)
    await log_action(action_type=AuditActionType.USER_LOGOUT, module="auth", actor_id=actor_id, actor_email=actor_email, actor_role=actor_role)
    return {"success": True, "message": "Logged out"}

@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    return {"success": True, "data": _u(current_user)}

@router.put("/me/password")
async def change_password(body: PasswordChangeRequest, current_user: dict = Depends(get_current_user)):
    if not verify_password(body.current_password, current_user.get("password_hash", "")): raise HTTPException(status_code=400, detail="Current password incorrect")
    await users_col().update_one({"_id": current_user["_id"]}, {"$set": {"password_hash": hash_password(body.new_password), "updated_at": datetime.now(timezone.utc)}})
    return {"success": True, "message": "Password updated"}

@router.post("/forgot-password")
async def forgot_password(body: PasswordResetRequest):
    user = await users_col().find_one({"email": body.email.lower()})
    if user:
        otp = generate_otp(); expiry = datetime.now(timezone.utc) + timedelta(minutes=settings.OTP_EXPIRY_MINUTES)
        await users_col().update_one({"_id": user["_id"]}, {"$set": {"otp_code": otp, "otp_expiry": expiry, "otp_purpose": "reset"}})
        send_otp_email(body.email, otp, purpose="reset")
    return {"success": True, "message": "If that email is registered, an OTP has been sent."}

@router.post("/reset-password")
async def reset_password(body: PasswordResetConfirmRequest):
    user = await users_col().find_one({"email": body.email.lower()})
    if not user or user.get("otp_code") != body.otp_code or user.get("otp_purpose") != "reset": raise HTTPException(status_code=400, detail="Invalid or expired OTP")
    otp_expiry = user.get("otp_expiry")
    if otp_expiry and datetime.now(timezone.utc) > otp_expiry: raise HTTPException(status_code=400, detail="OTP expired")
    await users_col().update_one({"_id": user["_id"]}, {"$set": {"password_hash": hash_password(body.new_password), "otp_code": None, "otp_expiry": None, "otp_purpose": None, "updated_at": datetime.now(timezone.utc)}})
    return {"success": True, "message": "Password reset successfully."}
