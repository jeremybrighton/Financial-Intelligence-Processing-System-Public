"""FRC System — Report Generation Router"""
import logging
from datetime import datetime, timezone
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from backend.core.database import case_reports_col, frc_cases_col, report_templates_col
from backend.core.dependencies import require_admin, require_admin_or_supervisor, require_any_frc_role, require_report_write
from backend.models.common import AuditActionType, ReportStatus
from backend.models.report import ReportCreateRequest, ReportFinaliseRequest, ReportTemplateCreateRequest, ReportUpdateRequest
from backend.services.audit_service import extract_actor, log_action

log = logging.getLogger(__name__)
router = APIRouter(tags=["Report Generation"])

def _s(doc):
    if doc and "_id" in doc: doc["_id"]=str(doc["_id"])
    return doc

@router.get("/reports/templates")
async def list_templates(current_user:dict=Depends(require_any_frc_role())):
    return {"success":True,"data":[_s(d) async for d in report_templates_col().find({"is_active":True})]}

@router.post("/reports/templates", status_code=201)
async def create_template(body:ReportTemplateCreateRequest,current_user:dict=Depends(require_admin())):
    if await report_templates_col().find_one({"template_code":body.template_code}): raise HTTPException(status_code=409,detail=f"Template '{body.template_code}' exists")
    now=datetime.now(timezone.utc)
    doc={**body.model_dump(),"is_active":True,"created_at":now,"updated_at":now}
    doc["sections"]=[s.model_dump() if hasattr(s,"model_dump") else s for s in body.sections]
    result=await report_templates_col().insert_one(doc); doc["_id"]=str(result.inserted_id)
    return {"success":True,"data":doc}

@router.get("/cases/{case_id}/reports")
async def list_case_reports(case_id:str,current_user:dict=Depends(require_any_frc_role())):
    return {"success":True,"data":[_s(d) async for d in case_reports_col().find({"case_id":case_id}).sort("created_at",-1)]}

@router.post("/cases/{case_id}/reports", status_code=201)
async def create_report(case_id:str,body:ReportCreateRequest,current_user:dict=Depends(require_report_write())):
    try: case=await frc_cases_col().find_one({"_id":ObjectId(case_id)})
    except: raise HTTPException(status_code=400,detail="Invalid case ID")
    if not case: raise HTTPException(status_code=404,detail="Case not found")
    template=await report_templates_col().find_one({"template_code":body.template_code,"is_active":True})
    if not template: raise HTTPException(status_code=404,detail=f"Template '{body.template_code}' not found")
    actor_id,actor_email,actor_role=extract_actor(current_user); now=datetime.now(timezone.utc)
    doc={"case_id":case_id,"case_number":case.get("case_number"),"template_id":str(template["_id"]),"template_code":body.template_code,"created_by":actor_id,"created_by_name":current_user.get("full_name",actor_email),"status":ReportStatus.DRAFT.value,"version":1,"content":body.content,"applicable_provisions":body.applicable_provisions,"review_notes":None,"finalised_by":None,"finalised_by_name":None,"finalised_at":None,"export_path":None,"created_at":now,"updated_at":now}
    result=await case_reports_col().insert_one(doc); doc["_id"]=str(result.inserted_id)
    await log_action(action_type=AuditActionType.REPORT_CREATED,module="report",actor_id=actor_id,actor_email=actor_email,actor_role=actor_role,target_entity="case_reports",target_id=str(result.inserted_id),details={"case_id":case_id,"template_code":body.template_code})
    return {"success":True,"data":doc}

@router.get("/cases/{case_id}/reports/{report_id}")
async def get_report(case_id:str,report_id:str,current_user:dict=Depends(require_any_frc_role())):
    try: doc=await case_reports_col().find_one({"_id":ObjectId(report_id),"case_id":case_id})
    except: raise HTTPException(status_code=400,detail="Invalid report ID")
    if not doc: raise HTTPException(status_code=404,detail="Not found")
    return {"success":True,"data":_s(doc)}

@router.put("/cases/{case_id}/reports/{report_id}")
async def update_report(case_id:str,report_id:str,body:ReportUpdateRequest,current_user:dict=Depends(require_report_write())):
    try: doc=await case_reports_col().find_one({"_id":ObjectId(report_id),"case_id":case_id})
    except: raise HTTPException(status_code=400,detail="Invalid report ID")
    if not doc: raise HTTPException(status_code=404,detail="Not found")
    if doc.get("status")==ReportStatus.FINALISED.value: raise HTTPException(status_code=400,detail="Cannot edit finalised report")
    updates={k:v for k,v in body.model_dump(exclude_none=True).items()}; updates["updated_at"]=datetime.now(timezone.utc); updates["version"]=doc.get("version",1)+1
    await case_reports_col().update_one({"_id":ObjectId(report_id)},{"$set":updates})
    return {"success":True,"data":_s(await case_reports_col().find_one({"_id":ObjectId(report_id)}))}

@router.post("/cases/{case_id}/reports/{report_id}/finalise")
async def finalise_report(case_id:str,report_id:str,body:ReportFinaliseRequest,current_user:dict=Depends(require_admin_or_supervisor())):
    try: doc=await case_reports_col().find_one({"_id":ObjectId(report_id),"case_id":case_id})
    except: raise HTTPException(status_code=400,detail="Invalid report ID")
    if not doc: raise HTTPException(status_code=404,detail="Not found")
    if doc.get("status")==ReportStatus.FINALISED.value: raise HTTPException(status_code=400,detail="Already finalised")
    actor_id,actor_email,actor_role=extract_actor(current_user); now=datetime.now(timezone.utc)
    await case_reports_col().update_one({"_id":ObjectId(report_id)},{"$set":{"status":ReportStatus.FINALISED.value,"finalised_by":actor_id,"finalised_by_name":current_user.get("full_name",actor_email),"finalised_at":now.isoformat(),"review_notes":body.review_notes,"updated_at":now}})
    await log_action(action_type=AuditActionType.REPORT_FINALISED,module="report",actor_id=actor_id,actor_email=actor_email,actor_role=actor_role,target_entity="case_reports",target_id=report_id,details={"case_id":case_id})
    return {"success":True,"data":_s(await case_reports_col().find_one({"_id":ObjectId(report_id)}))}
