"""Report request/response schemas."""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class ReportCreateRequest(BaseModel):
    frc_case_id: str
    report_type: str = Field(..., pattern=r"^(str|ctr|sar|other)$")
    title: str = Field(..., min_length=3, max_length=300)
    content: str = Field(..., min_length=10)
    legal_rule_ids: List[str] = []


class ReportUpdateRequest(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    legal_rule_ids: Optional[List[str]] = None


class ReportStatusUpdate(BaseModel):
    status: str = Field(..., pattern=r"^(draft|under_review|finalised)$")


class ReportResponse(BaseModel):
    id: str
    report_id: str
    frc_case_id: str
    institution_id: str
    report_type: str
    status: str
    title: str
    content: str
    prepared_by: str
    reviewed_by: Optional[str] = None
    finalised_at: Optional[datetime] = None
    legal_rule_ids: List[str]
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
