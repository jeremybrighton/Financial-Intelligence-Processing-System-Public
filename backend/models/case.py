from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from backend.models.common import CasePriority, CaseStatus, DocumentModel, SubmissionType

class CaseStatusUpdateRequest(BaseModel):
    status: CaseStatus; note: Optional[str] = Field(None, max_length=2000)

class CaseAssignRequest(BaseModel):
    user_id: str; note: Optional[str] = None

class CasePriorityUpdateRequest(BaseModel):
    priority: CasePriority; note: Optional[str] = None

class CaseUpdateRequest(BaseModel):
    summary: Optional[str] = None; case_type: Optional[str] = None; tags: Optional[List[str]] = None

class CaseNoteCreateRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000); is_internal: bool = True

class CaseEvidenceCreateRequest(BaseModel):
    evidence_type: str = Field(..., pattern=r"^(document|link|note|external_ref)$")
    label: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None; file_path: Optional[str] = None
    external_url: Optional[str] = None; source: Optional[str] = None
