from __future__ import annotations
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field
from backend.models.common import DocumentModel, ReferralStatus

class ReferralCreateRequest(BaseModel):
    destination_name: str = Field(..., min_length=2, max_length=200)
    destination_type: str = Field(..., pattern=r"^(police|central_bank|tax_authority|foreign_fiu|other)$")
    destination_contact: Optional[str] = None; notes: Optional[str] = None
    report_ids: List[str] = []

class ReferralStatusUpdateRequest(BaseModel):
    status: ReferralStatus; notes: Optional[str] = None

class ReferralOutcomeRequest(BaseModel):
    outcome: str = Field(..., min_length=2, max_length=2000); notes: Optional[str] = None
