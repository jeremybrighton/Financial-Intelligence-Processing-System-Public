"""
institutions collection document shape.

Fields:
  _id                ObjectId (auto)
  institution_code   str, unique  e.g. "KCB-001"
  institution_name   str
  institution_type   str: commercial_bank | sacco | payment_service_provider |
                          digital_credit_provider | insurance_provider |
                          microfinance_institution | investment_bank | other
  supervisory_body   str  e.g. "Central Bank of Kenya"
  contact_email      str
  status             str: active | inactive | suspended | pending
  is_active          bool (mirrors status == active)
  api_key_hash       str | None  (SHA-256 of raw key — raw key shown once at creation)
  api_key_suffix     str | None  (last 6 chars for display)
  created_at         datetime
  updated_at         datetime
"""
INSTITUTION_TYPES = [
    "commercial_bank", "sacco", "payment_service_provider",
    "digital_credit_provider", "insurance_provider",
    "microfinance_institution", "investment_bank", "other",
]
INSTITUTION_STATUSES = ["active", "inactive", "suspended", "pending"]
