from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field
from backend.models.common import DocumentModel

class LegalProvisionCreateRequest(BaseModel):
    provision_id: str = Field(..., min_length=3, max_length=50)
    source_document: str; document_year: Optional[int] = None
    section_number: str; section_title: str; full_text: str; summary: str
    applicable_offence_types: List[str] = []; reporting_obligations: List[str] = []
    penalty_range: Optional[str] = None; tags: List[str] = []; jurisdiction: str = "MU"

class LegalProvisionUpdateRequest(BaseModel):
    section_title: Optional[str] = None; full_text: Optional[str] = None
    summary: Optional[str] = None; applicable_offence_types: Optional[List[str]] = None
    reporting_obligations: Optional[List[str]] = None; penalty_range: Optional[str] = None
    tags: Optional[List[str]] = None; is_active: Optional[bool] = None
