from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from backend.models.common import DocumentModel, ReportStatus

class ReportSection(BaseModel):
    section_key: str; section_title: str; description: str
    required: bool = True; field_type: str = "text"; max_length: Optional[int] = None

class ReportTemplateCreateRequest(BaseModel):
    template_code: str = Field(..., min_length=3, max_length=30, pattern=r"^[A-Z0-9_]+$")
    name: str; description: str
    report_type: str = Field(..., pattern=r"^(str|ctr|cbt|sar|other)$")
    sections: List[ReportSection] = []; required_fields: List[str] = []
    legal_provision_tags: List[str] = []; version: str = "1.0"

class ReportCreateRequest(BaseModel):
    template_code: str; content: Dict[str, Any] = {}; applicable_provisions: List[str] = []

class ReportUpdateRequest(BaseModel):
    content: Optional[Dict[str, Any]] = None; applicable_provisions: Optional[List[str]] = None
    review_notes: Optional[str] = None

class ReportFinaliseRequest(BaseModel):
    review_notes: Optional[str] = None
