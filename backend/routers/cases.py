"""FRC System — Cases Router"""
import logging
from datetime import datetime, timezone
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from backend.core.database import case_timeline_col, frc_cases_col
from backend.core.dependencies import ROLE_FRC_ADMIN, get_current_user, require_admin_or_supervisor, require_any_frc_role, require_case_write
from backend.models.case import CaseAssignRequest, CaseEvidenceCreateRequest, CaseNoteCreateRequest, CasePriorityUpdateRequest, CaseStatusUpdateRequest, CaseUpdateRequest
from backend.services import case_service

log = logging.getLogger(__name__)
router = APIRouter(prefix="/cases", tags=["Case Management"])

@router.get("")
async def list_cases(status:str=None,priority:str=None,submission_type:str=None,institution_id:str=None,assigned_to:str=None,search:str=None,page:int=1,page_size:int=20,current_user:dict=Depends(require_any_frc_role())):
    result=await case_service.list_cases({"status":status,"priority":priority,"submission_type":submission_type,"institution_id":institution_id,"assigned_to":assigned_to,"search":search},page,page_size)
    return {"success":True,"data":result}

@router.get("/{case_id}")
async def get_case(case_id:str,current_user:dict=Depends(require_any_frc_role())):
    detail=await case_service.get_case_detail(case_id)
    if not detail: raise HTTPException(status_code=404,detail="Case not found")
    return {"success":True,"data":detail}

@router.put("/{case_id}")
async def update_case(case_id:str,body:CaseUpdateRequest,current_user:dict=Depends(require_case_write())):
    case=await case_service.get_case_by_id(case_id)
    if not case: raise HTTPException(status_code=404,detail="Case not found")
    updates={k:v for k,v in body.model_dump(exclude_none=True).items()}; updates["updated_at"]=datetime.now(timezone.utc)
    await frc_cases_col().update_one({"_id":ObjectId(case_id)},{"$set":updates})
    return {"success":True,"data":await case_service.get_case_by_id(case_id)}

@router.put("/{case_id}/status")
async def update_status(case_id:str,body:CaseStatusUpdateRequest,current_user:dict=Depends(require_case_write())):
    try: updated=await case_service.update_case_status(case_id,body.status,current_user,body.note,is_admin=current_user.get("role")==ROLE_FRC_ADMIN)
    except Exception as e: raise HTTPException(status_code=422,detail=str(e))
    return {"success":True,"data":updated}

@router.put("/{case_id}/assign")
async def assign_case(case_id:str,body:CaseAssignRequest,current_user:dict=Depends(require_admin_or_supervisor())):
    try: updated=await case_service.assign_case(case_id,body.user_id,current_user,body.note)
    except Exception as e: raise HTTPException(status_code=422,detail=str(e))
    return {"success":True,"data":updated}

@router.put("/{case_id}/priority")
async def update_priority(case_id:str,body:CasePriorityUpdateRequest,current_user:dict=Depends(require_case_write())):
    case=await case_service.get_case_by_id(case_id)
    if not case: raise HTTPException(status_code=404,detail="Case not found")
    await frc_cases_col().update_one({"_id":ObjectId(case_id)},{"$set":{"priority":body.priority.value,"updated_at":datetime.now(timezone.utc)}})
    return {"success":True,"data":await case_service.get_case_by_id(case_id)}

@router.get("/{case_id}/notes")
async def list_notes(case_id:str,page:int=1,page_size:int=20,current_user:dict=Depends(require_any_frc_role())):
    return {"success":True,"data":await case_service.list_notes(case_id,page,page_size)}

@router.post("/{case_id}/notes", status_code=201)
async def add_note(case_id:str,body:CaseNoteCreateRequest,current_user:dict=Depends(require_case_write())):
    note=await case_service.add_note(case_id,body.content,current_user,body.is_internal)
    return {"success":True,"data":note}

@router.get("/{case_id}/evidence")
async def list_evidence(case_id:str,current_user:dict=Depends(require_any_frc_role())):
    return {"success":True,"data":await case_service.list_evidence(case_id)}

@router.post("/{case_id}/evidence", status_code=201)
async def add_evidence(case_id:str,body:CaseEvidenceCreateRequest,current_user:dict=Depends(require_case_write())):
    ev=await case_service.add_evidence(case_id,body.model_dump(),current_user)
    return {"success":True,"data":ev}

@router.get("/{case_id}/timeline")
async def get_timeline(case_id:str,current_user:dict=Depends(require_any_frc_role())):
    items=[]; cursor=case_timeline_col().find({"case_id":case_id}).sort("timestamp",-1)
    async for d in cursor: d["_id"]=str(d["_id"]); items.append(d)
    return {"success":True,"data":items}
