"""
audit_logs collection document shape.

Fields:
  _id         ObjectId (auto)
  user_id     str | None  (None = system action)
  user_email  str | None
  user_role   str | None
  action      str  e.g. "user_login", "case_created", "institution_created"
  module      str  e.g. "auth", "cases", "institutions", "intake"
  target_id   str | None
  details     dict
  ip_address  str | None
  timestamp   datetime
"""
