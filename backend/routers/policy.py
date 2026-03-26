"""FRC System — Policy Rules Router"""
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from backend.core.database import policy_rules_col
from backend.core.dependencies import require_admin, require_any_frc_role
from backend.models.common import AuditActionType
from backend.models.policy import PolicyRuleCreateRequest, PolicyRuleUpdateRequest
from backend.services.audit_service import extract_actor, log_action
from backend.services.policy_service import evaluate_transaction

log = logging.getLogger(__name__)
router = APIRouter(prefix="/policy", tags=["Policy Engine"])

def _s(doc):
    if doc and "_id" in doc: doc["_id"]=str(doc["_id"])
    return doc

@router.get("/rules")
async def list_rules(active_only:bool=True,current_user:dict=Depends(require_any_frc_role())):
    query={"is_active":True} if active_only else {}
    return {"success":True,"data":[_s(d) async for d in policy_rules_col().find(query).sort("priority",1)]}

@router.post("/rules", status_code=201)
async def create_rule(body:PolicyRuleCreateRequest,current_user:dict=Depends(require_admin())):
    if await policy_rules_col().find_one({"rule_code":body.rule_code}): raise HTTPException(status_code=409,detail=f"Rule '{body.rule_code}' exists")
    now=datetime.now(timezone.utc)
    doc={**body.model_dump(),"is_active":True,"created_by":str(current_user["_id"]),"created_at":now,"updated_at":now}
    for f in ("rule_type","submission_type"):
        if hasattr(doc.get(f),"value"): doc[f]=doc[f].value
    result=await policy_rules_col().insert_one(doc); doc["_id"]=str(result.inserted_id)
    actor_id,actor_email,actor_role=extract_actor(current_user)
    await log_action(action_type=AuditActionType.POLICY_RULE_CREATED,module="policy",actor_id=actor_id,actor_email=actor_email,actor_role=actor_role,target_entity="policy_rules",target_id=str(result.inserted_id),details={"rule_code":body.rule_code})
    return {"success":True,"data":doc}

@router.get("/rules/{rule_code}")
async def get_rule(rule_code:str,current_user:dict=Depends(require_any_frc_role())):
    doc=await policy_rules_col().find_one({"rule_code":rule_code})
    if not doc: raise HTTPException(status_code=404,detail="Rule not found")
    return {"success":True,"data":_s(doc)}

@router.put("/rules/{rule_code}")
async def update_rule(rule_code:str,body:PolicyRuleUpdateRequest,current_user:dict=Depends(require_admin())):
    updates={k:v for k,v in body.model_dump(exclude_none=True).items()}; updates["updated_at"]=datetime.now(timezone.utc)
    result=await policy_rules_col().update_one({"rule_code":rule_code},{"$set":updates})
    if result.matched_count==0: raise HTTPException(status_code=404,detail="Rule not found")
    return {"success":True,"data":_s(await policy_rules_col().find_one({"rule_code":rule_code}))}

@router.delete("/rules/{rule_code}")
async def deactivate_rule(rule_code:str,current_user:dict=Depends(require_admin())):
    result=await policy_rules_col().update_one({"rule_code":rule_code},{"$set":{"is_active":False,"updated_at":datetime.now(timezone.utc)}})
    if result.matched_count==0: raise HTTPException(status_code=404,detail="Rule not found")
    return {"success":True,"message":f"Rule '{rule_code}' deactivated"}

@router.post("/evaluate")
async def evaluate(transaction:dict,current_user:dict=Depends(require_admin())):
    result=await evaluate_transaction(transaction)
    return {"success":True,"data":result.model_dump()}
