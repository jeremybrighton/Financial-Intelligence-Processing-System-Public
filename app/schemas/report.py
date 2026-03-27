"""
Report request/response schemas.
Reports are structured data records — no PDF generation at MVP stage.
Each report is linked to a case and optionally to legal rules.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

# Valid destination bodies aligned with the system mapping
DESTINATION_BODIES = [
    "FRC", "DCI", "KRA", "CBK", "EACC", "NIS",
    "ARA",           # Asset Recovery Agency
    "ANTI_TERROR",   # Anti-Terror Unit / National Counter Terrorism Centre
    "EGMONT",        # Egmont Group (international FIU channel)
    "CUSTOMS",       # KRA Customs
    "COMMITTEE",     # Counter Financing of Terrorism Inter-Ministerial Committee
    "OTHER",
]


class LegalBasis(BaseModel):
    """Structured reference to the legal justification for this report."""
    rule_code: Optional[str] = None
    act_name: Optional[str] = None
    section: Optional[str] = None
    summary: Optional[str] = None


class ReportCreateRequest(BaseModel):
    frc_case_id: str
    report_type: str = Field(
        ...,
        description="str | ctr | sar | cross_border | sanctions_freeze | terrorism_financing | corruption | other"
    )
    title: str = Field(..., min_length=3, max_length=300)
    summary: str = Field(..., min_length=10, max_length=5000,
                         description="Narrative summary of the case for this report")
    content: str = Field(..., min_length=10,
                         description="Full report content (structured text for MVP)")
    legal_basis: Optional[LegalBasis] = None
    legal_rule_ids: List[str] = []
    destination: str = Field(
        ...,
        description="Primary receiving authority: FRC | DCI | KRA | CBK | EACC | NIS | ARA | ANTI_TERROR | EGMONT | OTHER"
    )


class ReportUpdateRequest(BaseModel):
    title: Optional[str] = None
    summary: Optional[str] = None
    content: Optional[str] = None
    legal_basis: Optional[LegalBasis] = None
    legal_rule_ids: Optional[List[str]] = None
    destination: Optional[str] = None


class ReportStatusUpdate(BaseModel):
    status: str = Field(..., pattern=r"^(draft|under_review|finalised|sent)$")


class ReportResponse(BaseModel):
    id: str
    report_id: str
    frc_case_id: str
    institution_id: str
    report_type: str
    status: str
    title: str
    summary: str
    content: str
    legal_basis: Optional[Dict[str, Any]] = None
    legal_rule_ids: List[str]
    destination: str
    prepared_by: str
    reviewed_by: Optional[str] = None
    finalised_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
