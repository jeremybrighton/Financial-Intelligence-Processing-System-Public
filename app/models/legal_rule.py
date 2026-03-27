"""
legal_rules collection document shape.

Fields:
  _id                ObjectId (auto)
  rule_code          str, unique  e.g. "POCAMLA-S14"
  title              str
  source_document    str   e.g. "POCAMLA 2012"
  section            str   e.g. "Section 14(1)"
  summary            str
  full_text          str
  applicable_to      list[str]   e.g. ["money_laundering", "terrorist_financing"]
  reporting_obligation str | None
  penalty_range      str | None
  tags               list[str]
  is_active          bool
  created_at         datetime
  updated_at         datetime
"""
