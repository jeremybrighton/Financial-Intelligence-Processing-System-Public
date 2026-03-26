"""FRC System — Shared Pydantic Models and Enums"""
from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Any, Generic, List, Optional, TypeVar
from bson import ObjectId
from pydantic import BaseModel, Field
from pydantic.functional_validators import BeforeValidator
from typing_extensions import Annotated


def validate_object_id(v: Any) -> str:
    if isinstance(v, ObjectId): return str(v)
    if isinstance(v, str) and ObjectId.is_valid(v): return v
    raise ValueError(f"Invalid ObjectId: {v}")

PyObjectId = Annotated[str, BeforeValidator(validate_object_id)]

class DocumentModel(BaseModel):
    id: Optional[PyObjectId] = Field(None, alias="_id")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True, "json_encoders": {ObjectId: str, datetime: lambda v: v.isoformat()}}

T = TypeVar("T")
class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]; total: int; page: int; page_size: int; total_pages: int

class UserRole(str, Enum):
    FRC_ADMIN="frc_admin"; FRC_SUPERVISOR="frc_supervisor"; FRC_ANALYST="frc_analyst"
    FRC_INVESTIGATOR="frc_investigator"; FRC_AUDITOR="frc_auditor"

class InstitutionType(str, Enum):
    COMMERCIAL_BANK="commercial_bank"; MICROFINANCE="microfinance"; INSURANCE="insurance"
    FOREX_BUREAU="forex_bureau"; MOBILE_MONEY="mobile_money"; SECURITIES_FIRM="securities_firm"
    COOPERATIVE="cooperative"; OTHER="other"

class InstitutionStatus(str, Enum):
    ACTIVE="active"; SUSPENDED="suspended"; PENDING="pending"; REVOKED="revoked"

class SubmissionType(str, Enum):
    REGULATORY_REPORT="regulatory_report"; SUSPICIOUS_ACTIVITY_REPORT="suspicious_activity_report"

class SubmissionStatus(str, Enum):
    RECEIVED="received"; VALIDATED="validated"; ACCEPTED="accepted"
    REJECTED="rejected"; FLAGGED_FOR_REVIEW="flagged_for_review"

class CaseStatus(str, Enum):
    RECEIVED="received"; ACKNOWLEDGED="acknowledged"; UNDER_REVIEW="under_review"
    ON_HOLD="on_hold"; INVESTIGATION_COMPLETE="investigation_complete"
    REPORT_DRAFTED="report_drafted"; REPORT_UNDER_REVIEW="report_under_review"
    REPORT_REVISION_REQUIRED="report_revision_required"; REPORT_FINALISED="report_finalised"
    REFERRED="referred"; REFERRAL_ACKNOWLEDGED="referral_acknowledged"
    RESOLVED="resolved"; ARCHIVED="archived"; WITHDRAWN="withdrawn"

class CasePriority(str, Enum):
    LOW="low"; MEDIUM="medium"; HIGH="high"; CRITICAL="critical"

class ReportStatus(str, Enum):
    DRAFT="draft"; UNDER_REVIEW="under_review"; REVISION_REQUIRED="revision_required"; FINALISED="finalised"

class ReferralStatus(str, Enum):
    PENDING="pending"; SENT="sent"; ACKNOWLEDGED="acknowledged"; CLOSED="closed"

class PolicyRuleType(str, Enum):
    THRESHOLD_AMOUNT="threshold_amount"; CROSS_BORDER="cross_border"; ML_SCORE="ml_score"
    TRANSACTION_TYPE="transaction_type"; FREQUENCY="frequency"; GEOGRAPHIC="geographic"; COMBINED="combined"

class AuditActionType(str, Enum):
    USER_LOGIN="user_login"; USER_LOGOUT="user_logout"; USER_CREATED="user_created"
    USER_UPDATED="user_updated"; USER_DEACTIVATED="user_deactivated"; PASSWORD_RESET="password_reset"
    INSTITUTION_CREATED="institution_created"; INSTITUTION_UPDATED="institution_updated"
    INSTITUTION_SUSPENDED="institution_suspended"; API_KEY_ISSUED="api_key_issued"; API_KEY_REVOKED="api_key_revoked"
    SUBMISSION_RECEIVED="submission_received"; SUBMISSION_REJECTED="submission_rejected"
    CASE_CREATED="case_created"; CASE_ASSIGNED="case_assigned"; CASE_STATUS_CHANGED="case_status_changed"
    CASE_NOTE_ADDED="case_note_added"; CASE_EVIDENCE_ADDED="case_evidence_added"; CASE_WITHDRAWN="case_withdrawn"
    REPORT_CREATED="report_created"; REPORT_FINALISED="report_finalised"; REPORT_EXPORTED="report_exported"
    REFERRAL_CREATED="referral_created"; REFERRAL_SENT="referral_sent"; REFERRAL_OUTCOME_RECORDED="referral_outcome_recorded"
    LEGAL_PROVISION_ADDED="legal_provision_added"; LEGAL_PROVISION_UPDATED="legal_provision_updated"
    POLICY_RULE_CREATED="policy_rule_created"; POLICY_RULE_UPDATED="policy_rule_updated"; POLICY_RULE_DEACTIVATED="policy_rule_deactivated"
