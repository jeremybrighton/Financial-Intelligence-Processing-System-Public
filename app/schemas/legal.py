"""
Legal rules request/response schemas.
Aligned with POCAMLA 2009 (Revised 2023), POCAMLA Regulations 2023,
and terrorism/proliferation sanctions regulations.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class TriggerCondition(BaseModel):
    transaction_type: Optional[str] = None
    threshold: Optional[str] = None
    suspicion_required: Optional[bool] = None
    deadline: Optional[str] = None
    patterns: Optional[List[str]] = None
    events: Optional[List[str]] = None
    extra: Optional[Dict[str, Any]] = None


class SystemUse(BaseModel):
    bank_side: Optional[str] = None
    frc_side: Optional[str] = None


class LegalRuleCreateRequest(BaseModel):
    rule_code: str = Field(..., min_length=3, max_length=80, pattern=r"^[A-Z0-9\-_]+$")
    act_name: str = Field(..., min_length=2, max_length=400)
    section: str = Field(..., min_length=1, max_length=200)
    title: str = Field(..., min_length=2, max_length=300)
    summary: str
    full_text: Optional[str] = None
    rule_type: str = Field(
        ...,
        description="regulatory_threshold_rule | reporting_obligation | suspicious_activity_rule | declaration_requirement"
    )
    trigger_condition: Optional[TriggerCondition] = None
    threshold_value: Optional[str] = None     # e.g. "15000", "24", "7"
    threshold_unit: Optional[str] = None      # e.g. "USD", "HOURS", "YEARS", "WORKING_DAYS"
    suspicion_indicators: Optional[List[str]] = None
    case_type: str = Field(
        ...,
        description="suspicious_activity_report | regulatory_report | terrorism_sanctions_case | corruption_case"
    )
    destination_body: Optional[List[str]] = None   # ["FRC","DCI","KRA","CBK","EACC","NIS","ARA","ANTI_TERROR","EGMONT"]
    system_use: Optional[SystemUse] = None
    applicable_to: List[str] = []
    reporting_obligation: Optional[str] = None
    penalty_range: Optional[str] = None
    tags: List[str] = []


class LegalRuleUpdateRequest(BaseModel):
    title: Optional[str] = None
    summary: Optional[str] = None
    full_text: Optional[str] = None
    rule_type: Optional[str] = None
    threshold_value: Optional[str] = None
    threshold_unit: Optional[str] = None
    suspicion_indicators: Optional[List[str]] = None
    case_type: Optional[str] = None
    destination_body: Optional[List[str]] = None
    applicable_to: Optional[List[str]] = None
    reporting_obligation: Optional[str] = None
    penalty_range: Optional[str] = None
    tags: Optional[List[str]] = None
    is_active: Optional[bool] = None


class LegalRuleResponse(BaseModel):
    id: str
    rule_code: str
    act_name: str
    section: str
    title: str
    summary: str
    rule_type: str
    threshold_value: Optional[str] = None
    threshold_unit: Optional[str] = None
    suspicion_indicators: Optional[List[str]] = None
    case_type: str
    destination_body: Optional[List[str]] = None
    applicable_to: List[str]
    reporting_obligation: Optional[str] = None
    penalty_range: Optional[str] = None
    tags: List[str]
    is_active: bool
    created_at: Optional[datetime] = None


class LegalRuleDetailResponse(LegalRuleResponse):
    full_text: Optional[str] = None
    trigger_condition: Optional[Dict[str, Any]] = None
    system_use: Optional[Dict[str, Any]] = None
