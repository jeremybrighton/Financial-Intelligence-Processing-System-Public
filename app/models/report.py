"""
reports collection document shape.

Fields:
  _id             ObjectId (auto)
  report_id       str, unique  e.g. "RPT-2026-00001"
  frc_case_id     str  (ref: cases.frc_case_id)
  institution_id  str  (ref: institutions._id)
  report_type     str: str | ctr | sar | other
  status          str: draft | under_review | finalised
  title           str
  content         str
  prepared_by     str  (ref: users._id)
  reviewed_by     str | None
  finalised_at    datetime | None
  legal_rule_ids  list[str]
  created_at      datetime
  updated_at      datetime
"""
REPORT_TYPES = ["str", "ctr", "sar", "other"]
REPORT_STATUSES = ["draft", "under_review", "finalised"]
