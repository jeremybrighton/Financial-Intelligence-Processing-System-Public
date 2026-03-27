"""Referral request/response schemas."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ReferralCreateRequest(BaseModel):
    frc_case_id: str
    referred_to: str = Field(..., min_length=2, max_length=100)
    reason: str = Field(..., min_length=10, max_length=3000)
    notes: Optional[str] = Field(None, max_length=2000)


class ReferralStatusUpdate(BaseModel):
    status: str = Field(..., pattern=r"^(pending|sent|acknowledged|closed)$")
    notes: Optional[str] = Field(None, max_length=2000)


class ReferralResponse(BaseModel):
    id: str
    referral_id: str
    frc_case_id: str
    institution_id: str
    referred_to: str
    reason: str
    status: str
    notes: Optional[str] = None
    referred_by: str
    sent_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
