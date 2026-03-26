"""FRC System — Institutions Router"""
import logging
from datetime import datetime, timezone
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from backend.core.database import api_keys_col, institutions_col
from backend.core.dependencies import require_admin, require_admin_or_supervisor
from backend.core.security import generate_api_key, get_key_prefix, hash_api_key
from backend.models.common import AuditActionType
from backend.models.institution import ApiKeyCreateRequest, InstitutionCreateRequest, InstitutionUpdateRequest
from backend.services.audit_service import extract_actor, log_action

log = logging.getLogger(__name__)
router = APIRouter(prefix="/institutions", tags=["Institutions"])

def _s(doc):
    if doc and "_id" in doc: doc["_id"]=str(doc["_id"])
    return doc

@router.get("")
async def list_institutions(page:int=1,page_size:int=20,status:str=None,current_user:dict=Depends(require_admin_or_supervisor())):
    query={}
    if status: query["status"]=status
    skip=(page-1)*page_size; total=await institutions_col().count_documents(query)
    return {"success":True,"data":{"institutions":[_s(d) async for d in institutions_col().find(query).skip(skip).limit(page_size)],"total":total,"page":page}}

@router.post("", status_code=201)
async def create_institution(body:InstitutionCreateRequest, current_user:dict=Depends(require_admin())):
    if await institutions_col().find_one({"institution_code":body.institution_code}): raise HTTPException(status_code=409,detail=f"Code '{body.institution_code}' exists")
    now=datetime.now(timezone.utc)
    doc={**body.model_dump(),"is_active":True,"status":"active","submitted_case_count":0,"registration_date":now,"created_at":now,"updated_at":now}
    result=await institutions_col().insert_one(doc); doc["_id"]=str(result.inserted_id)
    actor_id,actor_email,actor_role=extract_actor(current_user)
    await log_action(action_type=AuditActionType.INSTITUTION_CREATED,module="institution",actor_id=actor_id,actor_email=actor_email,actor_role=actor_role,target_entity="institutions",target_id=str(result.inserted_id),details={"institution_code":body.institution_code})
    return {"success":True,"data":doc}

@router.get("/{institution_id}")
async def get_institution(institution_id:str,current_user:dict=Depends(require_admin_or_supervisor())):
    try: inst=await institutions_col().find_one({"_id":ObjectId(institution_id)})
    except: raise HTTPException(status_code=400,detail="Invalid ID")
    if not inst: raise HTTPException(status_code=404,detail="Not found")
    return {"success":True,"data":_s(inst)}

@router.put("/{institution_id}")
async def update_institution(institution_id:str,body:InstitutionUpdateRequest,current_user:dict=Depends(require_admin())):
    updates={k:v for k,v in body.model_dump(exclude_none=True).items()}
    if "status" in updates and hasattr(updates["status"],"value"): updates["status"]=updates["status"].value
    if "status" in updates: updates["is_active"]=updates["status"]=="active"
    updates["updated_at"]=datetime.now(timezone.utc)
    try: result=await institutions_col().update_one({"_id":ObjectId(institution_id)},{"$set":updates})
    except: raise HTTPException(status_code=400,detail="Invalid ID")
    if result.matched_count==0: raise HTTPException(status_code=404,detail="Not found")
    updated=await institutions_col().find_one({"_id":ObjectId(institution_id)})
    return {"success":True,"data":_s(updated)}

@router.post("/{institution_id}/api-keys", status_code=201)
async def issue_api_key(institution_id:str,body:ApiKeyCreateRequest,current_user:dict=Depends(require_admin())):
    try: inst=await institutions_col().find_one({"_id":ObjectId(institution_id)})
    except: raise HTTPException(status_code=400,detail="Invalid ID")
    if not inst: raise HTTPException(status_code=404,detail="Institution not found")
    if not inst.get("is_active"): raise HTTPException(status_code=400,detail="Institution not active")
    raw_key=generate_api_key(); key_hash=hash_api_key(raw_key); key_prefix=get_key_prefix(raw_key)
    now=datetime.now(timezone.utc)
    result=await api_keys_col().insert_one({"institution_id":institution_id,"key_hash":key_hash,"key_prefix":key_prefix,"label":body.label,"is_active":True,"expires_at":body.expires_at,"last_used_at":None,"created_by":str(current_user["_id"]),"created_at":now,"updated_at":now})
    actor_id,actor_email,actor_role=extract_actor(current_user)
    await log_action(action_type=AuditActionType.API_KEY_ISSUED,module="institution",actor_id=actor_id,actor_email=actor_email,actor_role=actor_role,target_entity="institution_api_keys",target_id=str(result.inserted_id),details={"institution_id":institution_id,"label":body.label})
    return {"success":True,"data":{"api_key":raw_key,"key_prefix":key_prefix,"label":body.label,"message":"Store this key securely. It will not be shown again."}}

@router.get("/{institution_id}/api-keys")
async def list_api_keys(institution_id:str,current_user:dict=Depends(require_admin())):
    keys=[]
    async for k in api_keys_col().find({"institution_id":institution_id},{"key_hash":0}):
        k["_id"]=str(k["_id"]); keys.append(k)
    return {"success":True,"data":keys}

@router.delete("/{institution_id}/api-keys/{key_id}")
async def revoke_api_key(institution_id:str,key_id:str,current_user:dict=Depends(require_admin())):
    try: result=await api_keys_col().update_one({"_id":ObjectId(key_id),"institution_id":institution_id},{"$set":{"is_active":False,"updated_at":datetime.now(timezone.utc)}})
    except: raise HTTPException(status_code=400,detail="Invalid key ID")
    if result.matched_count==0: raise HTTPException(status_code=404,detail="Key not found")
    actor_id,actor_email,actor_role=extract_actor(current_user)
    await log_action(action_type=AuditActionType.API_KEY_REVOKED,module="institution",actor_id=actor_id,actor_email=actor_email,actor_role=actor_role,target_entity="institution_api_keys",target_id=key_id)
    return {"success":True,"message":"API key revoked"}
