"""
users collection document shape.

Fields:
  _id           ObjectId (auto)
  email         str, unique
  full_name     str
  password_hash str
  role          str: frc_admin | frc_analyst | investigator | audit_viewer
  is_active     bool
  last_login    datetime | None
  created_at    datetime
  updated_at    datetime
"""
ROLES = ["frc_admin", "frc_analyst", "investigator", "audit_viewer"]
