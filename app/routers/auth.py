"""
Auth router.
POST /api/v1/auth/login   — login and get JWT token
GET  /api/v1/auth/me      — get current authenticated user
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from app.core.dependencies import get_current_user
from app.schemas.auth import LoginRequest, TokenResponse, UserResponse
from app.services import auth_service

log = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, request: Request):
    """
    Authenticate an FRC platform user.
    Returns a JWT access token and basic user info.
    """
    try:
        return await auth_service.login(
            body,
            ip_address=request.client.host if request.client else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    """Return the currently authenticated user's profile."""
    from app.schemas.common import serialize_doc
    from app.schemas.auth import UserResponse
    return UserResponse(**serialize_doc(current_user))
