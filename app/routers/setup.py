"""
FRC System — One-Time Setup / Seed Router
==========================================
POST /api/v1/setup/seed

Seeds the database with:
  - 4 FRC user accounts (admin, analyst, investigator, auditor)
  - 1 demo institution (FraudGuard Demo Bank) with an API key
  - 20 POCAMLA / POTA legal rules

Security:
  - Only executes when the users collection is EMPTY (no users at all).
  - If even one user exists, the endpoint returns 409 and does nothing.
  - Remove or disable this router once the system is live with real users.

This endpoint exists so Render-hosted deployments can be bootstrapped
without SSH / shell access to the production server.
"""
import hashlib
import logging
import secrets
import string
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from app.core.database import get_db
from app.core.security import hash_password

log = logging.getLogger(__name__)
router = APIRouter(prefix="/setup", tags=["Setup"])


@router.post("/seed", summary="Bootstrap — seed initial users and legal rules (only if DB is empty)")
async def seed_database():
    db = get_db()
    now = datetime.now(timezone.utc)

    # ── Guard: only run on an empty database ──────────────────────────────────
    user_count = await db["users"].count_documents({})
    if user_count > 0:
        raise HTTPException(
            status_code=409,
            detail=f"Database already has {user_count} user(s). Seed refused to prevent overwrite.",
        )

    created: dict = {"users": [], "institutions": [], "legal_rules": 0, "api_key": None}

    # ── Users ─────────────────────────────────────────────────────────────────
    user_seeds = [
        {"email": "admin@frc.go.ke",        "full_name": "FRC Administrator",   "password": "FRCAdmin2026!",   "role": "frc_admin"},
        {"email": "analyst@frc.go.ke",       "full_name": "FRC Analyst",          "password": "FRCAnalyst2026!", "role": "frc_analyst"},
        {"email": "investigator@frc.go.ke",  "full_name": "FRC Investigator",     "password": "FRCInvest2026!",  "role": "investigator"},
        {"email": "auditor@frc.go.ke",       "full_name": "FRC Audit Viewer",     "password": "FRCAudit2026!",   "role": "audit_viewer"},
    ]
    for u in user_seeds:
        await db["users"].insert_one({
            "email": u["email"],
            "full_name": u["full_name"],
            "password_hash": hash_password(u["password"]),
            "role": u["role"],
            "is_active": True,
            "last_login": None,
            "created_at": now,
            "updated_at": now,
        })
        created["users"].append(u["email"])
        log.info(f"Seeded user: {u['email']}")

    # ── Institution ───────────────────────────────────────────────────────────
    raw_key = "frc_" + "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(48))
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    key_suffix = raw_key[-6:]

    result = await db["institutions"].insert_one({
        "institution_code": "FRAUDGUARD-BANK",
        "institution_name": "FraudGuard Demo Bank",
        "institution_type": "commercial_bank",
        "supervisory_body": "Central Bank of Kenya",
        "contact_email": "compliance@fraudguard.bank",
        "status": "active",
        "is_active": True,
        "api_key_hash": key_hash,
        "api_key_suffix": key_suffix,
        "submission_count": 0,
        "created_at": now,
        "updated_at": now,
    })
    created["institutions"].append("FRAUDGUARD-BANK")
    created["api_key"] = raw_key
    log.info(f"Seeded institution: FRAUDGUARD-BANK (id={result.inserted_id})")

    # ── Legal Rules ───────────────────────────────────────────────────────────
    legal_rules = [
        {
            "rule_code": "POCAMLA-S44-STR-GENERAL",
            "act_name": "POCAMLA 2009 (Revised 2023)",
            "section": "Act s.44(1)-(3),(7),(11)",
            "title": "Suspicious Transaction / Activity Reporting (General)",
            "summary": "A reporting institution must monitor unusual, suspicious, large, and pattern-based transactions and report to the Centre within 2 days after suspicion arises, including attempted transactions.",
            "rule_type": "suspicious_activity_rule",
            "case_type": "suspicious_activity_report",
            "destination_body": ["FRC"],
            "tags": ["str", "sar", "suspicious_activity", "mandatory_reporting", "2_day_deadline"],
            "applicable_to": ["banks", "financial institutions", "DNFBPs", "all reporting institutions"],
            "reporting_obligation": "File STR within 2 days of suspicion with supporting documents",
            "penalty_range": "Up to KES 5,000,000 fine or 5 years imprisonment",
            "threshold_value": "2", "threshold_unit": "DAYS",
            "is_active": True, "created_at": now, "updated_at": now,
        },
        {
            "rule_code": "POCAMLA-S44-CASH-THRESHOLD",
            "act_name": "POCAMLA 2009 (Revised 2023) + POCAMLA Regulations 2023",
            "section": "Act s.44(6); Fourth Schedule; Regulation 40",
            "title": "Cash Transaction Threshold Report (CTR)",
            "summary": "All cash transactions at or above USD 15,000 must be reported to the Centre whether or not they appear suspicious.",
            "rule_type": "regulatory_threshold_rule",
            "case_type": "regulatory_report",
            "destination_body": ["FRC"],
            "tags": ["ctr", "cash_transaction", "threshold", "mandatory_reporting"],
            "applicable_to": ["banks", "financial institutions", "cash dealers"],
            "reporting_obligation": "File CTR by Friday of transaction week; urgent cases immediately",
            "penalty_range": "Up to KES 1,000,000 fine",
            "threshold_value": "15000", "threshold_unit": "USD",
            "is_active": True, "created_at": now, "updated_at": now,
        },
        {
            "rule_code": "POCAMLA-S12-REG10-CROSSBORDER",
            "act_name": "POCAMLA 2009 (Revised 2023) + POCAMLA Regulations 2023",
            "section": "Act s.12; Regulations 2023 reg.10",
            "title": "Cross-Border Monetary Instrument Declaration",
            "summary": "A person carrying monetary instruments into or out of Kenya at or above USD 10,000 must declare them to customs.",
            "rule_type": "declaration_requirement",
            "case_type": "regulatory_report",
            "destination_body": ["FRC", "KRA", "ARA"],
            "tags": ["cross_border", "declaration", "threshold", "customs"],
            "applicable_to": ["individuals", "travelers", "customs officers"],
            "reporting_obligation": "Declare to customs; customs forwards to FRC",
            "penalty_range": "Temporary seizure; reporting obligation",
            "threshold_value": "10000", "threshold_unit": "USD",
            "is_active": True, "created_at": now, "updated_at": now,
        },
        {
            "rule_code": "POCAMLA-REG38-STR-DETAIL",
            "act_name": "POCAMLA Regulations 2023",
            "section": "Regulation 38(1)-(3)",
            "title": "STR Filing — Reason and Deadline Obligation",
            "summary": "If a reporting institution becomes aware or ought to have become aware of suspicious activity indicating ML/TF/PF, it must report to the Centre within 2 days.",
            "rule_type": "reporting_obligation",
            "case_type": "suspicious_activity_report",
            "destination_body": ["FRC"],
            "tags": ["str", "2_day_deadline", "reporting_obligation"],
            "applicable_to": ["reporting institutions"],
            "reporting_obligation": "Report within 2 days; disclose suspicion reason; attach documents",
            "penalty_range": "Breach = criminal offence",
            "threshold_value": "2", "threshold_unit": "DAYS",
            "is_active": True, "created_at": now, "updated_at": now,
        },
        {
            "rule_code": "POCAMLA-REG37-SOURCE-OF-FUNDS",
            "act_name": "POCAMLA Regulations 2023",
            "section": "Regulation 37(1)(a)-(f), 37(2)-(3)",
            "title": "Large / Unusual Transactions — Source of Funds Challenge",
            "summary": "For large, frequent, or unusual cash deposits, withdrawals, exchanges, transfers, investments, or foreign transactions, the institution must obtain customer explanations.",
            "rule_type": "suspicious_activity_rule",
            "case_type": "suspicious_activity_report",
            "destination_body": ["FRC", "DCI", "KRA", "ARA"],
            "tags": ["source_of_funds", "unusual_activity", "edd", "pre_str"],
            "applicable_to": ["reporting institutions"],
            "reporting_obligation": "Obtain written explanation; escalate to STR if explanation fails",
            "penalty_range": "Failure to escalate = STR breach",
            "threshold_value": None, "threshold_unit": None,
            "is_active": True, "created_at": now, "updated_at": now,
        },
        {
            "rule_code": "POCAMLA-S45-CDD-IDENTITY",
            "act_name": "POCAMLA 2009 (Revised 2023)",
            "section": "Section 45(1)-(3)",
            "title": "Customer Due Diligence — Identity Verification",
            "summary": "Institutions must identify and verify customers and persons acting on their behalf before or during a business relationship or transaction.",
            "rule_type": "reporting_obligation",
            "case_type": "regulatory_report",
            "destination_body": ["FRC", "CBK"],
            "tags": ["kyc", "cdd", "identity_verification", "beneficial_owner"],
            "applicable_to": ["reporting institutions"],
            "reporting_obligation": "Apply CDD before/during all covered relationships and transactions",
            "penalty_range": "Up to KES 500,000 fine",
            "threshold_value": None, "threshold_unit": None,
            "is_active": True, "created_at": now, "updated_at": now,
        },
        {
            "rule_code": "POCAMLA-S45A-HIGH-RISK-COUNTRIES",
            "act_name": "POCAMLA 2009 (Revised 2023)",
            "section": "Section 45A(1)-(3)",
            "title": "Enhanced Due Diligence — High-Risk Countries",
            "summary": "Transactions and relationships connected to FATF-listed or Cabinet Secretary-identified higher-risk countries require enhanced due diligence.",
            "rule_type": "suspicious_activity_rule",
            "case_type": "suspicious_activity_report",
            "destination_body": ["FRC", "CBK", "NIS", "EGMONT"],
            "tags": ["edd", "high_risk_country", "fatf", "cross_border"],
            "applicable_to": ["reporting institutions"],
            "reporting_obligation": "Apply EDD; may require countermeasures or relationship termination",
            "penalty_range": "Non-compliance = regulatory breach",
            "threshold_value": None, "threshold_unit": None,
            "is_active": True, "created_at": now, "updated_at": now,
        },
        {
            "rule_code": "POCAMLA-S46-RECORD-KEEPING",
            "act_name": "POCAMLA 2009 (Revised 2023) + POCAMLA Regulations 2023",
            "section": "Act s.46; Regulations 2023 reg.42",
            "title": "Record Keeping — 7-Year Retention",
            "summary": "Institutions must keep transaction records and CDD records with full identifying detail for at least 7 years.",
            "rule_type": "reporting_obligation",
            "case_type": "regulatory_report",
            "destination_body": ["FRC", "CBK"],
            "tags": ["record_keeping", "7_year_retention", "compliance"],
            "applicable_to": ["reporting institutions"],
            "reporting_obligation": "Retain records 7 years; make available on request",
            "penalty_range": "Up to KES 500,000 fine",
            "threshold_value": "7", "threshold_unit": "YEARS",
            "is_active": True, "created_at": now, "updated_at": now,
        },
        {
            "rule_code": "POCAMLA-S47-INTERNAL-REPORTING",
            "act_name": "POCAMLA 2009 (Revised 2023)",
            "section": "Section 47",
            "title": "Internal Reporting Procedures",
            "summary": "Institutions must maintain internal escalation procedures so employees can report suspicion to a responsible compliance officer.",
            "rule_type": "reporting_obligation",
            "case_type": "regulatory_report",
            "destination_body": ["FRC"],
            "tags": ["internal_reporting", "compliance_officer", "escalation"],
            "applicable_to": ["reporting institutions"],
            "reporting_obligation": "Maintain internal reporting procedures; responsible officer must escalate",
            "penalty_range": "Breach = compliance failure",
            "threshold_value": None, "threshold_unit": None,
            "is_active": True, "created_at": now, "updated_at": now,
        },
        {
            "rule_code": "POCAMLA-S47A-REGISTRATION",
            "act_name": "POCAMLA 2009 (Revised 2023) + POCAMLA Regulations 2023",
            "section": "Act s.47A; Regulations 2023 reg.5",
            "title": "Institution Registration with the Centre",
            "summary": "Every reporting institution must register with the Centre, keep registration updated, and report suspicious transactions even if registration is outstanding.",
            "rule_type": "reporting_obligation",
            "case_type": "regulatory_report",
            "destination_body": ["FRC"],
            "tags": ["registration", "institution_registry", "compliance"],
            "applicable_to": ["all reporting institutions"],
            "reporting_obligation": "Register with FRC; update within 90 days of any change",
            "penalty_range": "Failure = offence",
            "threshold_value": "90", "threshold_unit": "DAYS",
            "is_active": True, "created_at": now, "updated_at": now,
        },
        {
            "rule_code": "POCAMLA-REG34-35-ONGOING-MONITORING",
            "act_name": "POCAMLA Regulations 2023",
            "section": "Regulations 34 and 35",
            "title": "Ongoing Customer Monitoring",
            "summary": "Institutions must continuously monitor customer accounts and business activity to ensure transactions match the customer's profile, business, and source of funds.",
            "rule_type": "suspicious_activity_rule",
            "case_type": "suspicious_activity_report",
            "destination_body": ["FRC", "DCI", "CBK", "NIS"],
            "tags": ["ongoing_monitoring", "cdd", "behavioural_analytics"],
            "applicable_to": ["reporting institutions"],
            "reporting_obligation": "Escalate to STR if monitoring reveals suspicion",
            "penalty_range": "Failure to monitor = compliance breach",
            "threshold_value": None, "threshold_unit": None,
            "is_active": True, "created_at": now, "updated_at": now,
        },
        {
            "rule_code": "POCAMLA-REG25-CDD-FAILURE-STR",
            "act_name": "POCAMLA Regulations 2023",
            "section": "Regulation 25(2), 25(6)",
            "title": "CDD Failure and Tipping-Off Prevention STR",
            "summary": "If a customer fails to provide identity evidence, do not open account. If full CDD would tip off a suspected money launderer, stop the process and file an STR instead.",
            "rule_type": "reporting_obligation",
            "case_type": "suspicious_activity_report",
            "destination_body": ["FRC", "DCI", "CBK"],
            "tags": ["cdd_failure", "tipping_off", "onboarding", "str"],
            "applicable_to": ["reporting institutions"],
            "reporting_obligation": "File STR where tipping-off concern prevents full CDD",
            "penalty_range": "Non-compliance = criminal offence",
            "threshold_value": None, "threshold_unit": None,
            "is_active": True, "created_at": now, "updated_at": now,
        },
        {
            "rule_code": "POCAMLA-S48-DNFBP-SCOPE",
            "act_name": "POCAMLA 2009 (Revised 2023)",
            "section": "Section 48",
            "title": "AML Obligations — Non-Bank Professionals (DNFBPs)",
            "summary": "AML reporting obligations extend to accountants, advocates, notaries, and trust/company service providers when they conduct specified financial transactions for clients.",
            "rule_type": "reporting_obligation",
            "case_type": "regulatory_report",
            "destination_body": ["FRC", "CBK"],
            "tags": ["dnfbp", "non_bank", "advocate", "accountant"],
            "applicable_to": ["accountants", "advocates", "notaries", "TCSPs"],
            "reporting_obligation": "Apply all AML obligations under Part IV; report where required",
            "penalty_range": "Same as for reporting institutions",
            "threshold_value": None, "threshold_unit": None,
            "is_active": True, "created_at": now, "updated_at": now,
        },
        {
            "rule_code": "POCAMLA-S44A-FRC-INTERVENTION",
            "act_name": "POCAMLA 2009 (Revised 2023)",
            "section": "Section 44A(1)-(2)",
            "title": "FRC No-Proceed / Transaction Intervention",
            "summary": "Where the Centre has reasonable grounds to suspect ML/TF/PF, it may order a transaction not to proceed for up to 5 working days.",
            "rule_type": "suspicious_activity_rule",
            "case_type": "suspicious_activity_report",
            "destination_body": ["FRC", "DCI", "KRA"],
            "tags": ["intervention", "no_proceed", "hold_order", "frc_power"],
            "applicable_to": ["FRC", "reporting institutions"],
            "reporting_obligation": "FRC issues written direction; institution must comply within 5 working days",
            "penalty_range": "Non-compliance = criminal offence",
            "threshold_value": "5", "threshold_unit": "WORKING_DAYS",
            "is_active": True, "created_at": now, "updated_at": now,
        },
        {
            "rule_code": "POTA-REG2023-FREEZE-ON-DESIGNATION",
            "act_name": "Prevention of Terrorism (UN SC Resolutions on Suppression of Terrorism) Regulations 2023",
            "section": "Regulations 2, 4, 6, 7",
            "title": "Terrorism Sanctions — Freeze on Designation (Without Delay)",
            "summary": "When a person or entity is designated under the terrorism sanctions framework, funds and property must be frozen without delay within 24 hours.",
            "rule_type": "reporting_obligation",
            "case_type": "suspicious_activity_report",
            "destination_body": ["FRC", "ANTI_TERROR", "COMMITTEE"],
            "tags": ["sanctions_freeze", "terrorism_financing", "24_hour_deadline", "designated_person"],
            "applicable_to": ["reporting institutions", "natural persons", "legal persons"],
            "reporting_obligation": "Freeze without delay (within 24 hours); no prior notice",
            "penalty_range": "Criminal offence for non-compliance",
            "threshold_value": "24", "threshold_unit": "HOURS",
            "is_active": True, "created_at": now, "updated_at": now,
        },
        {
            "rule_code": "POTA-REG2023-FREEZE-RETURNS",
            "act_name": "Prevention of Terrorism (UN SC Resolutions on Suppression of Terrorism) Regulations 2023",
            "section": "Regulation 30(1)-(3)",
            "title": "Post-Freeze Return and Attempted Dealing Report",
            "summary": "After a freeze, institutions must file a written return within 24 hours. Any attempted dealing with frozen property must also be reported within 24 hours.",
            "rule_type": "reporting_obligation",
            "case_type": "suspicious_activity_report",
            "destination_body": ["FRC", "COMMITTEE", "ANTI_TERROR", "DCI"],
            "tags": ["sanctions_freeze", "post_freeze_return", "24_hour_deadline"],
            "applicable_to": ["reporting institutions"],
            "reporting_obligation": "File written return within 24 hours; report attempted dealing",
            "penalty_range": "Non-compliance = criminal offence",
            "threshold_value": "24", "threshold_unit": "HOURS",
            "is_active": True, "created_at": now, "updated_at": now,
        },
        {
            "rule_code": "POTA-REG2023-SANCTIONS-MONITORING",
            "act_name": "Prevention of Terrorism (UN SC Resolutions on Suppression of Terrorism) Regulations 2023",
            "section": "Regulation 31",
            "title": "Ongoing Sanctions List Screening",
            "summary": "Institutions must regularly review domestic and sanctions lists and continuously monitor transactions involving listed entities.",
            "rule_type": "suspicious_activity_rule",
            "case_type": "suspicious_activity_report",
            "destination_body": ["FRC", "COMMITTEE", "ANTI_TERROR"],
            "tags": ["sanctions_screening", "terrorism_financing", "ongoing_monitoring"],
            "applicable_to": ["reporting institutions"],
            "reporting_obligation": "Ongoing screening; report matches and suspicious transactions to FRC",
            "penalty_range": "Failure = terrorism financing compliance breach",
            "threshold_value": None, "threshold_unit": None,
            "is_active": True, "created_at": now, "updated_at": now,
        },
        {
            "rule_code": "PF-REG2023-PROLIFERATION-SANCTIONS",
            "act_name": "Prevention of Terrorism (UN SC Resolutions on Proliferation Financing) Regulations 2023",
            "section": "Regulations 3, 4, 5",
            "title": "Proliferation Financing Sanctions — 24-Hour Implementation",
            "summary": "Proliferation-financing sanctions must be implemented within 24 hours of designation.",
            "rule_type": "reporting_obligation",
            "case_type": "regulatory_report",
            "destination_body": ["FRC", "COMMITTEE", "ANTI_TERROR"],
            "tags": ["proliferation_financing", "pf_sanctions", "24_hour_deadline"],
            "applicable_to": ["FRC", "reporting institutions", "supervisory bodies"],
            "reporting_obligation": "Implement within 24 hours; Committee Secretary circulates daily",
            "penalty_range": "Non-compliance = criminal offence",
            "threshold_value": "24", "threshold_unit": "HOURS",
            "is_active": True, "created_at": now, "updated_at": now,
        },
        {
            "rule_code": "PF-REG2023-COMPLIANCE-MONITORING",
            "act_name": "Prevention of Terrorism (Proliferation Financing) Regulations 2023",
            "section": "Regulation 12(1)-(3)",
            "title": "FRC Supervision of Proliferation Sanctions Compliance",
            "summary": "FRC, supervisory bodies, and self-regulatory bodies must monitor institutional compliance with proliferation sanctions.",
            "rule_type": "reporting_obligation",
            "case_type": "regulatory_report",
            "destination_body": ["FRC", "COMMITTEE"],
            "tags": ["proliferation_financing", "supervisory_monitoring", "sanctions_compliance"],
            "applicable_to": ["FRC", "supervisory bodies", "reporting institutions"],
            "reporting_obligation": "FRC monitors and can impose administrative sanctions",
            "penalty_range": "Administrative sanctions including fines",
            "threshold_value": None, "threshold_unit": None,
            "is_active": True, "created_at": now, "updated_at": now,
        },
        {
            "rule_code": "PF-REG2023-DELISTING-UNFREEZING",
            "act_name": "Prevention of Terrorism (Proliferation Financing) Regulations 2023",
            "section": "Regulations 13-16",
            "title": "Delisting and Unfreezing of Assets",
            "summary": "Where a designated person is delisted or a mistaken freeze is confirmed, funds must be unfrozen without delay.",
            "rule_type": "reporting_obligation",
            "case_type": "regulatory_report",
            "destination_body": ["FRC", "COMMITTEE"],
            "tags": ["delisting", "unfreezing", "sanctions_lifecycle", "remediation"],
            "applicable_to": ["reporting institutions", "Committee"],
            "reporting_obligation": "Unfreeze without delay upon confirmed delisting",
            "penalty_range": "Failure to unfreeze = regulatory breach",
            "threshold_value": None, "threshold_unit": None,
            "is_active": True, "created_at": now, "updated_at": now,
        },
    ]

    for rule in legal_rules:
        await db["legal_rules"].insert_one(rule)
    created["legal_rules"] = len(legal_rules)
    log.info(f"Seeded {len(legal_rules)} legal rules")

    log.info("Bootstrap seed complete.")

    return {
        "success": True,
        "message": "Database seeded successfully. Save the institution API key — it will not be shown again.",
        "data": {
            "users_created": created["users"],
            "institutions_created": created["institutions"],
            "legal_rules_created": created["legal_rules"],
            "institution_api_key": created["api_key"],
            "credentials": {
                "admin":        {"email": "admin@frc.go.ke",       "password": "FRCAdmin2026!"},
                "analyst":      {"email": "analyst@frc.go.ke",      "password": "FRCAnalyst2026!"},
                "investigator": {"email": "investigator@frc.go.ke", "password": "FRCInvest2026!"},
                "auditor":      {"email": "auditor@frc.go.ke",      "password": "FRCAudit2026!"},
            },
        },
    }
