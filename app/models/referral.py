"""
referrals collection document shape.

Fields:
  _id              ObjectId (auto)
  referral_id      str, unique  e.g. "REF-2026-00001"
  frc_case_id      str  (ref: cases.frc_case_id)
  institution_id   str  (ref: institutions._id)
  referred_to      str   e.g. "DCI", "KRA", "CBK", "EACC", "NIS"
  reason           str
  status           str: pending | sent | acknowledged | closed
  notes            str | None
  referred_by      str  (ref: users._id)
  sent_at          datetime | None
  acknowledged_at  datetime | None
  closed_at        datetime | None
  created_at       datetime
  updated_at       datetime
"""
REFERRAL_AGENCIES = ["DCI", "KRA", "CBK", "EACC", "NIS", "OTHER"]
REFERRAL_STATUSES = ["pending", "sent", "acknowledged", "closed"]
