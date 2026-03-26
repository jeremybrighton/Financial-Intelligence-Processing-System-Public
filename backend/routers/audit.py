"""FRC System — Audit Log Router"""
import logging
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from backend.core.database import audit_logs_col
from backend.core.dependencies import require_roles
from backend.models.common import UserRole

log = logging.getLogger(__name__)
router = APIRouter(prefix="/audit", tags=["Audit Log"])

_auditor_roles=require_roles(UserRole.FRC_ADMIN.value,UserRole.FRC_AUDITOR.value,UserRole.FRC_SUPERVISOR.value)

@router.get("/logs")
async def list_audit_logs(actor_id:str=None,action_type:str=None,module:str=None,target_id:str=None,page:int=1,page_size:int=50,current_user:dict=Depends(_auditor_roles)):
    query={}
    if actor_id: query["actor_id"]=actor_id
    if action_type: query["action_type"]=action_type
    if module: query["module"]=module
    if target_id: query["target_id"]=target_id
    skip=(page-1)*page_size; total=await audit_logs_col().count_documents(query)
    items=[]
    async for d in audit_logs_col().find(query).sort("timestamp",-1).skip(skip).limit(page_size): d["_id"]=str(d["_id"]); items.append(d)
    return {"success":True,"data":{"logs":items,"total":total,"page":page,"page_size":page_size,"total_pages":max(1,-(-total//page_size))}}

@router.get("/logs/{log_id}")
async def get_audit_log(log_id:str,current_user:dict=Depends(_auditor_roles)):
    try: doc=await audit_logs_col().find_one({"_id":ObjectId(log_id)})
    except: raise HTTPException(status_code=400,detail="Invalid log ID")
    if not doc: raise HTTPException(status_code=404,detail="Not found")
    doc["_id"]=str(doc["_id"]); return {"success":True,"data":doc}
