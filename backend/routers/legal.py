"""FRC System — Legal Knowledge Base Router"""
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from backend.core.database import legal_provisions_col
from backend.core.dependencies import require_admin, require_any_frc_role
from backend.models.common import AuditActionType
from backend.models.legal import LegalProvisionCreateRequest, LegalProvisionUpdateRequest
from backend.services.audit_service import extract_actor, log_action

log = logging.getLogger(__name__)
router = APIRouter(prefix="/legal", tags=["Legal Knowledge Base"])

def _s(doc):
    if doc and "_id" in doc: doc["_id"]=str(doc["_id"])
    return doc

@router.get("/provisions")
async def list_provisions(source_document:str=None,tag:str=None,offence_type:str=None,keyword:str=None,page:int=1,page_size:int=20,current_user:dict=Depends(require_any_frc_role())):
    query={"is_active":True}
    if source_document: query["source_document"]={"$regex":source_document,"$options":"i"}
    if tag: query["tags"]=tag
    if offence_type: query["applicable_offence_types"]=offence_type
    if keyword: query["$or"]=[{"section_title":{"$regex":keyword,"$options":"i"}},{"summary":{"$regex":keyword,"$options":"i"}}]
    skip=(page-1)*page_size; total=await legal_provisions_col().count_documents(query)
    cursor=legal_provisions_col().find(query,{"full_text":0}).skip(skip).limit(page_size)
    return {"success":True,"data":{"provisions":[_s(d) async for d in cursor],"total":total,"page":page}}

@router.post("/provisions", status_code=201)
async def create_provision(body:LegalProvisionCreateRequest,current_user:dict=Depends(require_admin())):
    if await legal_provisions_col().find_one({"provision_id":body.provision_id}): raise HTTPException(status_code=409,detail=f"Provision '{body.provision_id}' exists")
    now=datetime.now(timezone.utc)
    doc={**body.model_dump(),"is_active":True,"created_at":now,"updated_at":now}
    result=await legal_provisions_col().insert_one(doc); doc["_id"]=str(result.inserted_id)
    actor_id,actor_email,actor_role=extract_actor(current_user)
    await log_action(action_type=AuditActionType.LEGAL_PROVISION_ADDED,module="legal",actor_id=actor_id,actor_email=actor_email,actor_role=actor_role,target_entity="legal_provisions",target_id=str(result.inserted_id),details={"provision_id":body.provision_id})
    return {"success":True,"data":doc}

@router.get("/provisions/{provision_id}")
async def get_provision(provision_id:str,current_user:dict=Depends(require_any_frc_role())):
    doc=await legal_provisions_col().find_one({"provision_id":provision_id})
    if not doc: raise HTTPException(status_code=404,detail="Provision not found")
    return {"success":True,"data":_s(doc)}

@router.put("/provisions/{provision_id}")
async def update_provision(provision_id:str,body:LegalProvisionUpdateRequest,current_user:dict=Depends(require_admin())):
    updates={k:v for k,v in body.model_dump(exclude_none=True).items()}; updates["updated_at"]=datetime.now(timezone.utc)
    result=await legal_provisions_col().update_one({"provision_id":provision_id},{"$set":updates})
    if result.matched_count==0: raise HTTPException(status_code=404,detail="Not found")
    return {"success":True,"data":_s(await legal_provisions_col().find_one({"provision_id":provision_id}))}

@router.get("/suggest")
async def suggest_provisions(tags:str=None,offence_type:str=None,limit:int=10,current_user:dict=Depends(require_any_frc_role())):
    query={"is_active":True}; conditions=[]
    if tags:
        tag_list=[t.strip() for t in tags.split(",") if t.strip()]
        if tag_list: conditions.append({"tags":{"$in":tag_list}})
    if offence_type: conditions.append({"applicable_offence_types":offence_type})
    if conditions: query["$or"]=conditions
    cursor=legal_provisions_col().find(query,{"full_text":0}).limit(limit)
    return {"success":True,"data":[_s(d) async for d in cursor]}
