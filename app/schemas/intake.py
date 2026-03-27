"""
Intake API request/response schemas.
Receives structured suspicious/regulatory case reports from institutions.
NOT for raw transaction ingestion.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class EvidenceRef(BaseModel):
    """Metadata reference to a supporting document — no file upload required."""
    label: str
    reference_type: str = "document"   # document | url | note
    reference_value: Optional[str] = None
    description: Optional[str] = None


class IntakeRequest(BaseModel):
    """
    Payload posted by an institution system to submit a reportable case.
    The institution is identified via API key header — not in the payload.
    """
    external_report_id: Optional[str] = None   # Institution's own case reference
    report_type: str = Field(
        ...,
        pattern=r"^(suspicious_activity_report|regulatory_threshold_report)$",
        description="Type of report being submitted",
    )
    amount: Optional[float] = Field(None, ge=0)
    currency: Optional[str] = Field(None, min_length=3, max_length=3)
    transaction_summary: Optional[str] = Field(None, max_length=2000)
    triggering_rules: List[str] = Field(
        default_factory=list,
        description="Rule codes or indicator names that triggered this report",
    )
    risk_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    narrative: Optional[str] = Field(None, max_length=5000)
    timestamp: Optional[datetime] = None       # Original suspicious event time
    evidence_refs: List[EvidenceRef] = Field(default_factory=list)
    submission_metadata: Optional[Dict[str, Any]] = None


class IntakeAcknowledgement(BaseModel):
    """Returned immediately after successful case creation."""
    frc_case_id: str
    status: str = "received"
    message: str = "Case received successfully."
    received_at: datetime
