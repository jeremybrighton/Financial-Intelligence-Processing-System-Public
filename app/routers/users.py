"""
Users router (FRC admin manages FRC platform users).
GET    /api/v1/users
POST   /api/v1/users
GET    /api/v1/users/{user_id}
DELETE /api/v1/users/{user_id}   (deactivate — soft delete)
"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from app.core.dependencies import require_admin, require_admin_or_analyst
from app.schemas.auth import UserCreateRequest, UserResponse
from app.services import auth_service

log = logging.getLogger(__name__)
router = APIRouter(prefix="/users", tags=["Users"])


@router.get("", summary="List FRC users")
async def list_users(
    page: int = 1,
    page_size: int = 20,
    current_user: dict = Depends(require_admin_or_analyst()),
):
    result = await auth_service.list_users(page, page_size)
    return {"success": True, "data": result}


@router.post("", status_code=201, summary="Create a new FRC user")
async def create_user(
    body: UserCreateRequest,
    current_user: dict = Depends(require_admin()),
):
    try:
        user = await auth_service.create_user(body, created_by=current_user)
        return {"success": True, "data": user}
    except auth_service.ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/{user_id}", summary="Get user by ID")
async def get_user(
    user_id: str,
    current_user: dict = Depends(require_admin_or_analyst()),
):
    user = await auth_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"success": True, "data": user}


@router.delete("/{user_id}", summary="Deactivate a user")
async def deactivate_user(
    user_id: str,
    current_user: dict = Depends(require_admin()),
):
    if user_id == str(current_user.get("_id", "")):
        raise HTTPException(status_code=400, detail="Cannot deactivate your own account")
    ok = await auth_service.deactivate_user(user_id, actor=current_user)
    if not ok:
        raise HTTPException(status_code=404, detail="User not found")
    return {"success": True, "message": "User deactivated"}
