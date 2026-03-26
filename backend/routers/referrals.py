"""FRC System — Referrals Router"""
import logging
from datetime import datetime, timezone
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from backend.core.database import frc_cases_col, referrals_col
from backend.core.dependencies import require_admin_or_supervisor, require_any_frc_role, require_case_write
from backend.models.common import AuditActionType, ReferralStatus
from backend.models.referral import ReferralCreateRequest, ReferralOutcomeRequest, ReferralStatusUpdateRequest
from backend.services.audit_service import extract_actor, log_action

log = logging.getLogger(__name__)
router = APIRouter(tags=["Referrals"])

def _s(doc):
    if doc and "_id" in doc: doc["_id"]=str(doc["_id"])
    return doc

@router.get("/cases/{case_id}/referrals")
async def list_referrals(case_id:str,current_user:dict=Depends(require_any_frc_role())):
    return {"success":True,"data":[_s(d) async for d in referrals_col().find({"case_id":case_id}).sort("created_at",-1)]}

@router.post("/cases/{case_id}/referrals", status_code=201)
async def create_referral(case_id:str,body:ReferralCreateRequest,current_user:dict=Depends(require_case_write())):
    try: case=await frc_cases_col().find_one({"_id":ObjectId(case_id)})
    except: raise HTTPException(status_code=400,detail="Invalid case ID")
    if not case: raise HTTPException(status_code=404,detail="Case not found")
    actor_id,actor_email,actor_role=extract_actor(current_user); now=datetime.now(timezone.utc)
    doc={"case_id":case_id,"case_number":case.get("case_number"),"created_by":actor_id,"created_by_name":current_user.get("full_name",actor_email),"destination_name":body.destination_name,"destination_type":body.destination_type,"destination_contact":body.destination_contact,"status":ReferralStatus.PENDING.value,"report_ids":body.report_ids,"notes":body.notes,"sent_at":None,"acknowledged_at":None,"outcome":None,"outcome_recorded_at":None,"outcome_recorded_by":None,"closed_at":None,"created_at":now,"updated_at":now}
    result=await referrals_col().insert_one(doc); doc["_id"]=str(result.inserted_id)
    await log_action(action_type=AuditActionType.REFERRAL_CREATED,module="referral",actor_id=actor_id,actor_email=actor_email,actor_role=actor_role,target_entity="referrals",target_id=str(result.inserted_id),details={"case_id":case_id,"destination":body.destination_name})
    return {"success":True,"data":doc}

@router.put("/cases/{case_id}/referrals/{referral_id}/status")
async def update_referral_status(case_id:str,referral_id:str,body:ReferralStatusUpdateRequest,current_user:dict=Depends(require_case_write())):
    try: referral=await referrals_col().find_one({"_id":ObjectId(referral_id),"case_id":case_id})
    except: raise HTTPException(status_code=400,detail="Invalid referral ID")
    if not referral: raise HTTPException(status_code=404,detail="Not found")
    now=datetime.now(timezone.utc); updates={"status":body.status.value,"updated_at":now}
    if body.notes: updates["notes"]=body.notes
    if body.status==ReferralStatus.SENT: updates["sent_at"]=now
    elif body.status==ReferralStatus.ACKNOWLEDGED: updates["acknowledged_at"]=now
    elif body.status==ReferralStatus.CLOSED: updates["closed_at"]=now
    await referrals_col().update_one({"_id":ObjectId(referral_id)},{"$set":updates})
    return {"success":True,"data":_s(await referrals_col().find_one({"_id":ObjectId(referral_id)}))}

@router.post("/cases/{case_id}/referrals/{referral_id}/outcome")
async def record_outcome(case_id:str,referral_id:str,body:ReferralOutcomeRequest,current_user:dict=Depends(require_case_write())):
    try: referral=await referrals_col().find_one({"_id":ObjectId(referral_id),"case_id":case_id})
    except: raise HTTPException(status_code=400,detail="Invalid referral ID")
    if not referral: raise HTTPException(status_code=404,detail="Not found")
    actor_id,actor_email,actor_role=extract_actor(current_user); now=datetime.now(timezone.utc)
    await referrals_col().update_one({"_id":ObjectId(referral_id)},{"$set":{"outcome":body.outcome,"outcome_recorded_at":now,"outcome_recorded_by":actor_id,"status":ReferralStatus.CLOSED.value,"closed_at":now,"updated_at":now}})
    await log_action(action_type=AuditActionType.REFERRAL_OUTCOME_RECORDED,module="referral",actor_id=actor_id,actor_email=actor_email,actor_role=actor_role,target_entity="referrals",target_id=referral_id)
    return {"success":True,"data":_s(await referrals_col().find_one({"_id":ObjectId(referral_id)}))}

@router.get("/referrals")
async def list_all_referrals(status:str=None,page:int=1,page_size:int=20,current_user:dict=Depends(require_admin_or_supervisor())):
    query={}
    if status: query["status"]=status
    skip=(page-1)*page_size; total=await referrals_col().count_documents(query)
    return {"success":True,"data":{"referrals":[_s(d) async for d in referrals_col().find(query).sort("created_at",-1).skip(skip).limit(page_size)],"total":total,"page":page}}
