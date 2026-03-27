"""
cases collection document shape.

Fields:
  _id                ObjectId (auto)
  frc_case_id        str, unique  e.g. "FRC-2026-00001"
  institution_id     str  (ref: institutions._id)
  institution_code   str
  external_report_id str | None  (institution's own case/report ref)
  report_type        str: suspicious_activity_report | regulatory_threshold_report
  status             str: received | under_review | report_generated | referred | closed
  priority           str: low | medium | high
  summary            str | None
  analyst_notes      str | None
  amount             float | None
  currency           str | None
  transaction_summary str | None
  triggering_rules   list[str]
  risk_score         float | None
  narrative          str | None
  evidence_refs      list[dict]  (metadata only, no file uploads)
  submission_metadata dict
  linked_report_id   str | None
  linked_legal_rule_ids list[str]
  referral_id        str | None
  created_at         datetime
  updated_at         datetime
"""
REPORT_TYPES = ["suspicious_activity_report", "regulatory_threshold_report"]
CASE_STATUSES = ["received", "under_review", "report_generated", "referred", "closed"]
CASE_PRIORITIES = ["low", "medium", "high"]
