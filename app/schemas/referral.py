"""
Referral request/response schemas.
Referral tracking module — routes FRC cases to destination authorities.

Supported destination bodies:
  FRC, DCI, KRA, CBK, EACC, NIS, ARA (Asset Recovery Agency),
  ANTI_TERROR (Anti-Terror Unit / NCTC), EGMONT, CUSTOMS, COMMITTEE, OTHER
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

REFERRAL_DESTINATIONS = [
    "FRC", "DCI", "KRA", "CBK", "EACC", "NIS",
    "ARA", "ANTI_TERROR", "EGMONT", "CUSTOMS", "COMMITTEE", "OTHER",
]

REFERRAL_STATUSES = ["pending", "sent", "acknowledged", "closed"]


class ReferralCreateRequest(BaseModel):
    frc_case_id: str
    destination_body: str = Field(
        ...,
        description=(
            "Target authority: FRC | DCI | KRA | CBK | EACC | NIS | "
            "ARA | ANTI_TERROR | EGMONT | CUSTOMS | COMMITTEE | OTHER"
        )
    )
    reason: str = Field(..., min_length=10, max_length=3000,
                        description="Legal and factual basis for the referral")
    case_type: Optional[str] = Field(
        None,
        description=(
            "suspicious_activity_report | regulatory_report | "
            "terrorism_sanctions_case | corruption_case | cross_border_case | "
            "sanctions_freeze_case | proliferation_financing_case"
        )
    )
    routing_policy: Optional[str] = Field(
        None, max_length=1000,
        description="Notes on why this destination was chosen"
    )
    notes: Optional[str] = Field(None, max_length=2000)
    report_ids: List[str] = Field(default_factory=list,
                                  description="Report IDs attached to this referral")


class ReferralStatusUpdate(BaseModel):
    status: str = Field(..., pattern=r"^(pending|sent|acknowledged|closed)$")
    notes: Optional[str] = Field(None, max_length=2000)


class ReferralResponse(BaseModel):
    id: str
    referral_id: str
    frc_case_id: str
    institution_id: str
    destination_body: str
    reason: str
    case_type: Optional[str] = None
    routing_policy: Optional[str] = None
    status: str
    notes: Optional[str] = None
    report_ids: List[str] = []
    referred_by: str
    sent_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
