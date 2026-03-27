"""
Legal rules router.
GET    /api/v1/legal/rules
POST   /api/v1/legal/rules
GET    /api/v1/legal/rules/{rule_code}
PUT    /api/v1/legal/rules/{rule_code}
"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from app.core.dependencies import require_admin, require_any_internal_role
from app.schemas.legal import LegalRuleCreateRequest, LegalRuleUpdateRequest
from app.services import legal_service

log = logging.getLogger(__name__)
router = APIRouter(prefix="/legal", tags=["Legal Rules"])


@router.get("/rules", summary="List legal rules")
async def list_rules(
    page: int = 1,
    page_size: int = 20,
    tag: str = None,
    applicable_to: str = None,
    search: str = None,
    active_only: bool = True,
    current_user: dict = Depends(require_any_internal_role()),
):
    result = await legal_service.list_rules(page, page_size, tag, applicable_to, search, active_only)
    return {"success": True, "data": result}


@router.post("/rules", status_code=201, summary="Add a legal rule")
async def create_rule(
    body: LegalRuleCreateRequest,
    current_user: dict = Depends(require_admin()),
):
    try:
        rule = await legal_service.create_rule(body, actor=current_user)
        return {"success": True, "data": rule}
    except legal_service.ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/rules/{rule_code}", summary="Get legal rule detail")
async def get_rule(
    rule_code: str,
    current_user: dict = Depends(require_any_internal_role()),
):
    rule = await legal_service.get_rule(rule_code)
    if not rule:
        raise HTTPException(status_code=404, detail=f"Rule '{rule_code}' not found")
    return {"success": True, "data": rule}


@router.put("/rules/{rule_code}", summary="Update a legal rule")
async def update_rule(
    rule_code: str,
    body: LegalRuleUpdateRequest,
    current_user: dict = Depends(require_admin()),
):
    rule = await legal_service.update_rule(rule_code, body, actor=current_user)
    if not rule:
        raise HTTPException(status_code=404, detail=f"Rule '{rule_code}' not found")
    return {"success": True, "data": rule}
