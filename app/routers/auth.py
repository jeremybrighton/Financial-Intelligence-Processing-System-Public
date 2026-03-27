"""
Auth router.
POST /api/v1/auth/login
GET  /api/v1/auth/me
POST /api/v1/auth/change-password
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from app.core.dependencies import get_current_user
from app.schemas.auth import LoginRequest, PasswordChangeRequest, TokenResponse, UserResponse
from app.schemas.common import serialize_doc
from app.services import auth_service

log = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, request: Request):
    """Login and receive a JWT access token."""
    try:
        return await auth_service.login(
            body, ip_address=request.client.host if request.client else None
        )
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    """Return the currently authenticated user's profile."""
    return UserResponse(**serialize_doc(dict(current_user)))


@router.post("/change-password")
async def change_password(
    body: PasswordChangeRequest,
    current_user: dict = Depends(get_current_user),
):
    """Change the authenticated user's own password."""
    user_id = str(current_user.get("_id", ""))
    try:
        await auth_service.change_password(
            user_id, body.current_password, body.new_password, actor=current_user
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"success": True, "message": "Password updated successfully"}
