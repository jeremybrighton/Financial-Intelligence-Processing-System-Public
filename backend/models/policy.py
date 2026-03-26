from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from backend.models.common import DocumentModel, PolicyRuleType, SubmissionType

class PolicyRuleCreateRequest(BaseModel):
    rule_code: str = Field(..., min_length=3, max_length=50, pattern=r"^[A-Z0-9_]+$")
    name: str; description: str; rule_type: PolicyRuleType; submission_type: SubmissionType
    priority: int = Field(100, ge=1, le=999); conditions: Dict[str, Any] = {}; legal_basis: Optional[str] = None

class PolicyRuleUpdateRequest(BaseModel):
    name: Optional[str] = None; description: Optional[str] = None
    is_active: Optional[bool] = None; priority: Optional[int] = None
    conditions: Optional[Dict[str, Any]] = None; legal_basis: Optional[str] = None

class PolicyEvaluationResult(BaseModel):
    triggered: bool; matched_rules: List[str]; submission_type: Optional[SubmissionType] = None
    highest_priority_rule: Optional[str] = None; reason: str = ""
