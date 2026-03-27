"""Case management request/response schemas."""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class CaseStatusUpdate(BaseModel):
    status: str = Field(
        ...,
        pattern=r"^(received|under_review|report_generated|referred|closed)$",
    )


class CasePatchRequest(BaseModel):
    priority: Optional[str] = Field(None, pattern=r"^(low|medium|high)$")
    summary: Optional[str] = Field(None, max_length=2000)
    analyst_notes: Optional[str] = Field(None, max_length=5000)


class CaseResponse(BaseModel):
    id: str
    frc_case_id: str
    institution_id: str
    institution_code: str
    external_report_id: Optional[str] = None
    report_type: str
    status: str
    priority: str
    summary: Optional[str] = None
    analyst_notes: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    transaction_summary: Optional[str] = None
    triggering_rules: List[str] = []
    risk_score: Optional[float] = None
    narrative: Optional[str] = None
    evidence_refs: List[Dict[str, Any]] = []
    linked_report_id: Optional[str] = None
    linked_legal_rule_ids: List[str] = []
    referral_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class CaseListResponse(BaseModel):
    cases: List[CaseResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
