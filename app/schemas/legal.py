"""Legal rules request/response schemas."""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class LegalRuleCreateRequest(BaseModel):
    rule_code: str = Field(..., min_length=3, max_length=60, pattern=r"^[A-Z0-9\-_]+$")
    title: str = Field(..., min_length=2, max_length=300)
    source_document: str
    section: str
    summary: str
    full_text: str
    applicable_to: List[str] = []
    reporting_obligation: Optional[str] = None
    penalty_range: Optional[str] = None
    tags: List[str] = []


class LegalRuleUpdateRequest(BaseModel):
    title: Optional[str] = None
    summary: Optional[str] = None
    full_text: Optional[str] = None
    applicable_to: Optional[List[str]] = None
    reporting_obligation: Optional[str] = None
    penalty_range: Optional[str] = None
    tags: Optional[List[str]] = None
    is_active: Optional[bool] = None


class LegalRuleResponse(BaseModel):
    id: str
    rule_code: str
    title: str
    source_document: str
    section: str
    summary: str
    applicable_to: List[str]
    reporting_obligation: Optional[str] = None
    penalty_range: Optional[str] = None
    tags: List[str]
    is_active: bool
    created_at: Optional[datetime] = None


class LegalRuleDetailResponse(LegalRuleResponse):
    full_text: str
