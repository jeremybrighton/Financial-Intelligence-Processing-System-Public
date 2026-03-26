from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from backend.models.common import DocumentModel, SubmissionStatus, SubmissionType

class TransactionDetails(BaseModel):
    transaction_ref: str; transaction_type: Optional[str] = None
    amount: float = Field(..., ge=0); currency: str = Field("USD", min_length=3, max_length=3)
    amount_usd_equivalent: Optional[float] = None; transaction_date: datetime
    channel: Optional[str] = None; is_cross_border: bool = False
    origin_country: Optional[str] = None; destination_country: Optional[str] = None
    sender_account: Optional[str] = None; sender_name: Optional[str] = None
    sender_id_type: Optional[str] = None; sender_id_number: Optional[str] = None
    recipient_account: Optional[str] = None; recipient_name: Optional[str] = None
    recipient_bank: Optional[str] = None
    ml_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    ml_risk_level: Optional[str] = None; ml_model_version: Optional[str] = None
    sender_balance_before: Optional[float] = None; sender_balance_after: Optional[float] = None
    extra_fields: Optional[Dict[str, Any]] = None

class SubmissionPayload(BaseModel):
    institution_ref: str; source_system: str = "fraudguard"
    source_batch_id: Optional[str] = None; transaction: TransactionDetails
    triggered_rules: List[str] = Field(..., min_length=1)
    submission_type: SubmissionType; analyst_notes: Optional[str] = None
    suspicion_indicators: Optional[List[str]] = None
    supporting_evidence: Optional[Dict[str, Any]] = None
    submitted_at: Optional[datetime] = None

class IntakeAcknowledgement(BaseModel):
    success: bool = True; frc_case_id: str; submission_id: str
    submission_type: SubmissionType; status: SubmissionStatus
    received_at: datetime; message: str = "Submission received and FRC case created."
