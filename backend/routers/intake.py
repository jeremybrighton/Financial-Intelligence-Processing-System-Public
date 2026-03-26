"""FRC System — Intake Router (automatic policy-driven submissions)"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from backend.core.database import case_submissions_col
from backend.core.dependencies import get_institution_from_api_key, require_admin_or_supervisor, require_any_frc_role
from backend.models.intake import SubmissionPayload
from backend.services.intake_service import process_submission

log = logging.getLogger(__name__)
router = APIRouter(prefix="/intake", tags=["Case Intake"])

@router.post("/submit", status_code=201, summary="Receive automatic case submission from institution system")
async def submit_case(body: SubmissionPayload, request: Request, institution: dict=Depends(get_institution_from_api_key)):
    if body.institution_ref != institution["institution_code"]:
        raise HTTPException(status_code=403, detail=f"institution_ref '{body.institution_ref}' does not match authenticated institution '{institution['institution_code']}'")
    ack = await process_submission(payload=body, institution=institution, submission_ip=request.client.host if request.client else None)
    return {"success": True, "data": ack.model_dump(mode="json")}

@router.get("/submissions", dependencies=[Depends(require_any_frc_role())])
async def list_submissions(page:int=1,page_size:int=20,submission_type:str=None,status:str=None,institution_id:str=None):
    query={}
    if submission_type: query["submission_type"]=submission_type
    if status: query["status"]=status
    if institution_id: query["institution_id"]=institution_id
    skip=(page-1)*page_size; total=await case_submissions_col().count_documents(query)
    cursor=case_submissions_col().find(query,{"payload":0}).sort("received_at",-1).skip(skip).limit(page_size)
    items=[]
    async for d in cursor: d["_id"]=str(d["_id"]); items.append(d)
    return {"success":True,"data":{"submissions":items,"total":total,"page":page,"page_size":page_size,"total_pages":max(1,-(-total//page_size))}}

@router.get("/submissions/{submission_id}", dependencies=[Depends(require_admin_or_supervisor())])
async def get_submission(submission_id: str):
    from bson import ObjectId
    try: doc=await case_submissions_col().find_one({"_id":ObjectId(submission_id)})
    except: raise HTTPException(status_code=400,detail="Invalid submission ID")
    if not doc: raise HTTPException(status_code=404,detail="Not found")
    doc["_id"]=str(doc["_id"]); return {"success":True,"data":doc}
