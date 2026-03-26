"""FRC System — Users Router"""
import logging
from datetime import datetime, timezone
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from backend.core.database import users_col
from backend.core.dependencies import require_admin, require_admin_or_supervisor
from backend.core.security import hash_password
from backend.models.common import AuditActionType
from backend.models.user import UserCreateRequest, UserUpdateRequest
from backend.services.audit_service import extract_actor, log_action

log = logging.getLogger(__name__)
router = APIRouter(prefix="/users", tags=["Users"])

def _s(doc):
    if doc:
        doc["_id"] = str(doc["_id"])
        doc.pop("password_hash", None); doc.pop("otp_code", None)
    return doc

@router.get("")
async def list_users(page: int=1, page_size: int=20, current_user: dict=Depends(require_admin_or_supervisor())):
    skip=(page-1)*page_size; total=await users_col().count_documents({})
    cursor=users_col().find({},{"password_hash":0,"otp_code":0}).skip(skip).limit(page_size)
    return {"success":True,"data":{"users":[_s(d) async for d in cursor],"total":total,"page":page}}

@router.post("", status_code=201)
async def create_user(body: UserCreateRequest, current_user: dict=Depends(require_admin())):
    if await users_col().find_one({"email":body.email.lower()}): raise HTTPException(status_code=409,detail="Email already registered")
    now=datetime.now(timezone.utc)
    doc={"email":body.email.lower(),"full_name":body.full_name,"password_hash":hash_password(body.password),"role":body.role.value,"is_active":True,"created_at":now,"updated_at":now}
    result=await users_col().insert_one(doc); doc["_id"]=str(result.inserted_id)
    actor_id,actor_email,actor_role=extract_actor(current_user)
    await log_action(action_type=AuditActionType.USER_CREATED,module="auth",actor_id=actor_id,actor_email=actor_email,actor_role=actor_role,target_entity="users",target_id=str(result.inserted_id),details={"email":body.email,"role":body.role.value})
    doc.pop("password_hash",None); return {"success":True,"data":doc}

@router.get("/{user_id}")
async def get_user(user_id: str, current_user: dict=Depends(require_admin_or_supervisor())):
    try: user=await users_col().find_one({"_id":ObjectId(user_id)},{"password_hash":0,"otp_code":0})
    except: raise HTTPException(status_code=400,detail="Invalid user ID")
    if not user: raise HTTPException(status_code=404,detail="User not found")
    return {"success":True,"data":_s(user)}

@router.put("/{user_id}")
async def update_user(user_id: str, body: UserUpdateRequest, current_user: dict=Depends(require_admin())):
    updates={k:v for k,v in body.model_dump(exclude_none=True).items()}
    if "role" in updates and hasattr(updates["role"],"value"): updates["role"]=updates["role"].value
    updates["updated_at"]=datetime.now(timezone.utc)
    try: result=await users_col().update_one({"_id":ObjectId(user_id)},{"$set":updates})
    except: raise HTTPException(status_code=400,detail="Invalid user ID")
    if result.matched_count==0: raise HTTPException(status_code=404,detail="User not found")
    updated=await users_col().find_one({"_id":ObjectId(user_id)},{"password_hash":0})
    return {"success":True,"data":_s(updated)}

@router.delete("/{user_id}")
async def deactivate_user(user_id: str, current_user: dict=Depends(require_admin())):
    if user_id==str(current_user["_id"]): raise HTTPException(status_code=400,detail="Cannot deactivate own account")
    try: result=await users_col().update_one({"_id":ObjectId(user_id)},{"$set":{"is_active":False,"updated_at":datetime.now(timezone.utc)}})
    except: raise HTTPException(status_code=400,detail="Invalid user ID")
    if result.matched_count==0: raise HTTPException(status_code=404,detail="User not found")
    return {"success":True,"message":"User deactivated"}
