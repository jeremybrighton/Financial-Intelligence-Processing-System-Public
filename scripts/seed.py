"""
FRC System — Database Seed Script
====================================
Creates:
  1. FRC admin user
  2. FRC analyst user
  3. Demo investigator user
  4. Demo institution (FraudGuard Bank) + API key
  5. 20 structured POCAMLA / POTA legal rules

Run from project root:
  MONGODB_URI=<uri> JWT_SECRET_KEY=<any> python scripts/seed.py

Set RESET=true to wipe and re-seed existing data.
"""
import asyncio
import hashlib
import os
import secrets
import string
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.server_api import ServerApi
from passlib.context import CryptContext

pwd   = CryptContext(schemes=["bcrypt"], deprecated="auto")
URI   = os.environ.get("MONGODB_URI")
DB    = os.environ.get("MONGODB_DB_NAME", "frc_db")
RESET = os.environ.get("RESET", "false").lower() == "true"

if not URI:
    raise ValueError("MONGODB_URI environment variable is required")


async def upsert(db, col, filt, doc, label):
    existing = await db[col].find_one(filt)
    if existing and not RESET:
        print(f"  [SKIP] {label}")
        return existing["_id"]
    if existing:
        await db[col].delete_one(filt)
    r = await db[col].insert_one(doc)
    print(f"  [OK]   {label}")
    return r.inserted_id


async def seed():
    print(f"\n{'='*60}")
    print("Financial Intelligence Processing System — Seed")
    print(f"DB: {DB}  |  RESET={RESET}")
    print(f"{'='*60}\n")

    client = AsyncIOMotorClient(URI, server_api=ServerApi("1"), tls=True)
    db = client[DB]
    now = datetime.now(timezone.utc)

    # ── Users ──────────────────────────────────────────────────────────────────
    print("Users:")
    await upsert(db, "users", {"email": "admin@frc.go.ke"}, {
        "email": "admin@frc.go.ke", "full_name": "FRC Administrator",
        "password_hash": pwd.hash("FRCAdmin2026!"), "role": "frc_admin",
        "is_active": True, "last_login": None, "created_at": now, "updated_at": now,
    }, "admin@frc.go.ke  /  FRCAdmin2026!")

    await upsert(db, "users", {"email": "analyst@frc.go.ke"}, {
        "email": "analyst@frc.go.ke", "full_name": "Demo FRC Analyst",
        "password_hash": pwd.hash("FRCAnalyst2026!"), "role": "frc_analyst",
        "is_active": True, "last_login": None, "created_at": now, "updated_at": now,
    }, "analyst@frc.go.ke  /  FRCAnalyst2026!")

    await upsert(db, "users", {"email": "investigator@frc.go.ke"}, {
        "email": "investigator@frc.go.ke", "full_name": "Demo Investigator",
        "password_hash": pwd.hash("FRCInvest2026!"), "role": "investigator",
        "is_active": True, "last_login": None, "created_at": now, "updated_at": now,
    }, "investigator@frc.go.ke  /  FRCInvest2026!")

    await upsert(db, "users", {"email": "auditor@frc.go.ke"}, {
        "email": "auditor@frc.go.ke", "full_name": "Demo Audit Viewer",
        "password_hash": pwd.hash("FRCAudit2026!"), "role": "audit_viewer",
        "is_active": True, "last_login": None, "created_at": now, "updated_at": now,
    }, "auditor@frc.go.ke  /  FRCAudit2026!")

    # ── Institution ────────────────────────────────────────────────────────────
    print("\nInstitutions:")
    inst_code = "FRAUDGUARD-BANK"
    inst_existing = await db["institutions"].find_one({"institution_code": inst_code})

    if inst_existing and not RESET:
        print(f"  [SKIP] {inst_code}")
        inst_id = inst_existing["_id"]
        has_key = bool(inst_existing.get("api_key_hash"))
    else:
        if inst_existing: await db["institutions"].delete_one({"institution_code": inst_code})
        r = await db["institutions"].insert_one({
            "institution_code": inst_code, "institution_name": "FraudGuard Demo Bank",
            "institution_type": "commercial_bank", "supervisory_body": "Central Bank of Kenya",
            "contact_email": "compliance@fraudguard.bank", "status": "active", "is_active": True,
            "api_key_hash": None, "api_key_suffix": None, "submission_count": 0,
            "created_at": now, "updated_at": now,
        })
        inst_id = r.inserted_id
        has_key = False
        print(f"  [OK]   {inst_code}")

    if not has_key or RESET:
        raw_key = "frc_" + "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(48))
        await db["institutions"].update_one(
            {"_id": inst_id},
            {"$set": {"api_key_hash": hashlib.sha256(raw_key.encode()).hexdigest(), "api_key_suffix": raw_key[-6:], "updated_at": now}},
        )
        print(f"\n  {'!'*56}")
        print(f"  Institution API Key for {inst_code}:")
        print(f"\n  {raw_key}\n")
        print(f"  Set in FraudGuard env: FRC_API_KEY={raw_key}")
        print(f"  FRC_INTAKE_URL=https://<render-url>/api/v1/intake/cases")
        print(f"\n  SAVE THIS KEY — shown only once.")
        print(f"  {'!'*56}\n")

    # ── Legal Rules — 20 POCAMLA / POTA rules ──────────────────────────────────
    print("Legal Rules:")
    legal_rules = [
        {
            "rule_code": "POCAMLA-S12-REG10-CROSSBORDER",
            "act_name": "POCAMLA 2009 (Revised 2023) + POCAMLA Regulations 2023",
            "section": "Act s.12; Regulations 2023 reg.10",
            "title": "Cross-Border Monetary Instrument Declaration",
            "summary": "A person carrying monetary instruments into or out of Kenya at or above USD 10,000 must declare them to customs. False declaration or non-declaration may lead to seizure and reporting.",
            "full_text": "Act section 12 and Regulation 10(1)-(6) require declaration at port of entry/exit. Customs forwards declarations to the Centre. Non-declaration or false declaration triggers inspection, temporary seizure, and mandatory reporting.",
            "rule_type": "declaration_requirement",
            "trigger_condition": {"transaction_type": "cross_border_conveyance_of_monetary_instruments", "threshold": "USD 10,000 or equivalent", "additional_trigger": "false declaration or failure to declare"},
            "threshold_value": "10000", "threshold_unit": "USD",
            "suspicion_indicators": ["cross-border cash movement at or above threshold", "missing declaration evidence", "travel profile matches large cash deposit"],
            "case_type": "regulatory_report",
            "destination_body": ["FRC", "KRA", "ARA"],
            "system_use": {"bank_side": "Flag for EDD and source-of-funds review when customer discloses inbound/outbound cross-border cash at or above threshold.", "frc_side": "Customs declaration intake, false-declaration alert workflow, seizure tracking, repeat-declarant analytics."},
            "applicable_to": ["individuals", "travelers", "customs officers"],
            "reporting_obligation": "Declare to customs; customs forwards to FRC",
            "penalty_range": "Temporary seizure; reporting obligation",
            "tags": ["cross_border", "declaration", "threshold", "customs"],
            "is_active": True, "created_at": now, "updated_at": now,
        },
        {
            "rule_code": "POCAMLA-S44-STR-GENERAL",
            "act_name": "POCAMLA 2009 (Revised 2023)",
            "section": "Act s.44(1)-(3),(7),(11)",
            "title": "Suspicious Transaction / Activity Reporting (General)",
            "summary": "A reporting institution must monitor unusual, suspicious, large, and pattern-based transactions and report to the Centre within 2 days after suspicion arises, including attempted transactions.",
            "full_text": "Section 44 requires institutions to monitor complex, unusual, suspicious, large, and periodic-pattern transactions. Report to FRC within 2 days including attempted transactions and supporting documents.",
            "rule_type": "suspicious_activity_rule",
            "trigger_condition": {"suspicion_basis": ["complex transaction", "unusual transaction", "suspicious transaction", "large transaction", "unusual pattern", "attempted suspicious transaction"], "deadline": "within 2 days after suspicion arose"},
            "threshold_value": "2", "threshold_unit": "DAYS",
            "suspicion_indicators": ["complex or unusual transaction structure", "no apparent economic purpose", "attempted suspicious transaction", "unusual pattern across time periods"],
            "case_type": "suspicious_activity_report",
            "destination_body": ["FRC"],
            "system_use": {"bank_side": "Core STR engine. Trigger from anomaly detection, rules, structuring, unexplained fund movement, unusual account behaviour.", "frc_side": "STR intake, evidence attachment, deadline tracking from suspicion date, analyst triage queue."},
            "applicable_to": ["banks", "financial institutions", "DNFBPs", "all reporting institutions"],
            "reporting_obligation": "File STR within 2 days of suspicion with supporting documents",
            "penalty_range": "Up to KES 5,000,000 fine or 5 years imprisonment",
            "tags": ["str", "sar", "suspicious_activity", "mandatory_reporting", "2_day_deadline"],
            "is_active": True, "created_at": now, "updated_at": now,
        },
        {
            "rule_code": "POCAMLA-REG38-STR-DETAIL",
            "act_name": "POCAMLA Regulations 2023",
            "section": "Regulation 38(1)-(3)",
            "title": "STR Filing — Reason and Deadline Obligation",
            "summary": "If a reporting institution becomes aware or ought to have become aware of suspicious activity indicating ML/TF/PF, it must report to the Centre within 2 days and disclose the nature and reason for suspicion.",
            "full_text": "Regulation 38 formalises the STR duty. The standard includes actual awareness and constructive awareness. The institution must state the nature and reason for suspicion and attach available supporting documents.",
            "rule_type": "reporting_obligation",
            "trigger_condition": {"knowledge_standard": ["actual awareness", "ought reasonably to have become aware"], "deadline": "within 2 days"},
            "threshold_value": "2", "threshold_unit": "DAYS",
            "suspicion_indicators": ["reasonable grounds for suspicion regardless of certainty"],
            "case_type": "suspicious_activity_report",
            "destination_body": ["FRC"],
            "system_use": {"bank_side": "Use as the legal timer for STR countdown once an alert becomes a formal suspicion.", "frc_side": "Store suspicion_arose_at, reported_at, narrative grounds, attachment completeness, late-report breach flags."},
            "applicable_to": ["reporting institutions"],
            "reporting_obligation": "Report within 2 days; disclose suspicion reason; attach documents",
            "penalty_range": "Breach = criminal offence",
            "tags": ["str", "2_day_deadline", "reporting_obligation", "constructive_knowledge"],
            "is_active": True, "created_at": now, "updated_at": now,
        },
        {
            "rule_code": "POCAMLA-S44-CASH-THRESHOLD",
            "act_name": "POCAMLA 2009 (Revised 2023) + POCAMLA Regulations 2023",
            "section": "Act s.44(6); Fourth Schedule; Regulation 40",
            "title": "Cash Transaction Threshold Report (CTR)",
            "summary": "All cash transactions at or above USD 15,000 must be reported to the Centre whether or not they appear suspicious. Reporting is by Friday of the week unless urgent.",
            "full_text": "Section 44(6) and the Fourth Schedule set the USD 15,000 threshold. Regulation 40 governs electronic filing by the end of the week in which the transaction occurred.",
            "rule_type": "regulatory_threshold_rule",
            "trigger_condition": {"transaction_type": "cash_transaction", "threshold": "USD 15,000 or equivalent", "suspicion_required": False},
            "threshold_value": "15000", "threshold_unit": "USD",
            "suspicion_indicators": [],
            "case_type": "regulatory_report",
            "destination_body": ["FRC"],
            "system_use": {"bank_side": "Automatic CTR generation for all qualifying cash transactions independent of fraud score.", "frc_side": "Separate regulatory threshold intake from STR intake; support weekly batch filing and urgent same-day filing."},
            "applicable_to": ["banks", "financial institutions", "cash dealers"],
            "reporting_obligation": "File CTR by Friday of transaction week; urgent cases immediately",
            "penalty_range": "Up to KES 1,000,000 fine",
            "tags": ["ctr", "cash_transaction", "threshold", "mandatory_reporting", "no_suspicion_required"],
            "is_active": True, "created_at": now, "updated_at": now,
        },
        {
            "rule_code": "POCAMLA-REG37-SOURCE-OF-FUNDS",
            "act_name": "POCAMLA Regulations 2023",
            "section": "Regulation 37(1)(a)-(f), 37(2)-(3)",
            "title": "Large / Unusual Transactions — Source of Funds Challenge",
            "summary": "For large, frequent, or unusual cash deposits, withdrawals, exchanges, transfers, investments, or foreign transactions, the institution must obtain customer explanations and supporting documents.",
            "full_text": "Regulation 37 covers multiple categories of unusual activity. The institution must seek written customer explanation and source-of-funds documents. Escalate to STR if legitimacy remains doubtful.",
            "rule_type": "suspicious_activity_rule",
            "trigger_condition": {"patterns": ["large/frequent/unusual cash deposits or withdrawals", "large/frequent currency exchanges", "multiple or nominee accounts", "unusual transfers/payments", "unusual investments", "unusual foreign transactions"]},
            "threshold_value": None, "threshold_unit": None,
            "suspicion_indicators": ["volume inconsistent with profile", "nominee account activity", "unusual foreign corridor", "missing purpose documents"],
            "case_type": "suspicious_activity_report",
            "destination_body": ["FRC", "DCI", "KRA", "ARA"],
            "system_use": {"bank_side": "Trigger source-of-funds review and pre-STR escalation logic.", "frc_side": "Require institutions to include whether customer explanation was sought and what documents were provided."},
            "applicable_to": ["reporting institutions"],
            "reporting_obligation": "Obtain written explanation; escalate to STR if explanation fails",
            "penalty_range": "Failure to escalate = STR breach",
            "tags": ["source_of_funds", "unusual_activity", "edd", "pre_str"],
            "is_active": True, "created_at": now, "updated_at": now,
        },
        {
            "rule_code": "POCAMLA-REG34-35-ONGOING-MONITORING",
            "act_name": "POCAMLA Regulations 2023",
            "section": "Regulations 34 and 35",
            "title": "Ongoing Customer Monitoring",
            "summary": "Institutions must continuously monitor customer accounts and business activity to ensure transactions match the customer's profile, business, and source of funds.",
            "full_text": "Regulations 34-35 require continuous, risk-sensitive monitoring. Institutions must update KYC/CDD and scrutinize all activity against known customer profile.",
            "rule_type": "suspicious_activity_rule",
            "trigger_condition": {"relationship_status": "ongoing customer relationship", "monitoring_need": "continuous and risk-sensitive"},
            "threshold_value": None, "threshold_unit": None,
            "suspicion_indicators": ["transaction deviates from historical baseline", "sudden volume spike", "new high-risk corridor or counterparty", "outdated customer profile"],
            "case_type": "suspicious_activity_report",
            "destination_body": ["FRC", "DCI", "CBK", "NIS"],
            "system_use": {"bank_side": "Supports behavioural monitoring, peer baselines, expected-vs-actual pattern checks.", "frc_side": "Check whether institution had ongoing monitoring controls and whether missed detection points exist."},
            "applicable_to": ["reporting institutions"],
            "reporting_obligation": "Escalate to STR if monitoring reveals suspicion",
            "penalty_range": "Failure to monitor = compliance breach",
            "tags": ["ongoing_monitoring", "cdd", "behavioural_analytics", "risk_sensitive"],
            "is_active": True, "created_at": now, "updated_at": now,
        },
        {
            "rule_code": "POCAMLA-REG25-CDD-FAILURE-STR",
            "act_name": "POCAMLA Regulations 2023",
            "section": "Regulation 25(2), 25(6)",
            "title": "CDD Failure and Tipping-Off Prevention STR",
            "summary": "If a customer fails to provide identity evidence, do not open account. If full CDD would tip off a suspected money launderer or terrorist, stop the process and file an STR instead.",
            "full_text": "Regulation 25(2) prevents account opening without identity evidence. Regulation 25(6) allows institutions to skip full CDD and file an STR instead where pursuing it would alert the subject.",
            "rule_type": "reporting_obligation",
            "trigger_condition": {"trigger_events": ["customer fails to provide identity", "institution fears full CDD would tip off subject"]},
            "threshold_value": None, "threshold_unit": None,
            "suspicion_indicators": ["identity documents unavailable", "suspicious onboarding request", "KYC failure with suspicious context"],
            "case_type": "suspicious_activity_report",
            "destination_body": ["FRC", "DCI", "CBK"],
            "system_use": {"bank_side": "Link failed-KYC events and high-risk onboarding attempts directly into STR escalation workflow.", "frc_side": "Create special case subtype for onboarding or CDD-failure-based suspicion."},
            "applicable_to": ["reporting institutions"],
            "reporting_obligation": "File STR where tipping-off concern prevents full CDD",
            "penalty_range": "Non-compliance = criminal offence",
            "tags": ["cdd_failure", "tipping_off", "onboarding", "str"],
            "is_active": True, "created_at": now, "updated_at": now,
        },
        {
            "rule_code": "POCAMLA-S45-CDD-IDENTITY",
            "act_name": "POCAMLA 2009 (Revised 2023)",
            "section": "Section 45(1)-(3)",
            "title": "Customer Due Diligence — Identity Verification",
            "summary": "Institutions must identify and verify customers and persons acting on their behalf before or during a business relationship or transaction.",
            "full_text": "Section 45 requires institutions to apply CDD at account opening and during transactions. This includes identifying the customer, verifying identity, and identifying authorized representatives and beneficial owners.",
            "rule_type": "reporting_obligation",
            "trigger_condition": {"events": ["new business relationship", "customer transaction", "person acting on behalf of customer"]},
            "threshold_value": None, "threshold_unit": None,
            "suspicion_indicators": ["unverified customer", "incomplete beneficial owner identification", "third-party acting without clear authority"],
            "case_type": "regulatory_report",
            "destination_body": ["FRC", "CBK"],
            "system_use": {"bank_side": "Mandatory onboarding validation gate and beneficial-owner collection rule.", "frc_side": "CDD completeness as compliance field during inspections and case review."},
            "applicable_to": ["reporting institutions"],
            "reporting_obligation": "Apply CDD before/during all covered relationships and transactions",
            "penalty_range": "Up to KES 500,000 fine",
            "tags": ["kyc", "cdd", "identity_verification", "beneficial_owner"],
            "is_active": True, "created_at": now, "updated_at": now,
        },
        {
            "rule_code": "POCAMLA-S45A-HIGH-RISK-COUNTRIES",
            "act_name": "POCAMLA 2009 (Revised 2023)",
            "section": "Section 45A(1)-(3)",
            "title": "Enhanced Due Diligence — High-Risk Countries",
            "summary": "Transactions and relationships connected to FATF-listed or Cabinet Secretary-identified higher-risk countries require enhanced due diligence and possible countermeasures.",
            "full_text": "Section 45A requires enhanced CDD for relationships or transactions involving persons from FATF-identified or Cabinet Secretary-identified higher-risk jurisdictions.",
            "rule_type": "suspicious_activity_rule",
            "trigger_condition": {"country_risk": ["FATF strategic deficiencies list", "Cabinet Secretary identified jurisdiction"]},
            "threshold_value": None, "threshold_unit": None,
            "suspicion_indicators": ["transaction from/to high-risk jurisdiction", "correspondent bank in high-risk country", "cross-border flow with opaque ownership"],
            "case_type": "suspicious_activity_report",
            "destination_body": ["FRC", "CBK", "NIS", "EGMONT"],
            "system_use": {"bank_side": "Country-risk engine for payments, onboarding, correspondent banking.", "frc_side": "Jurisdiction-risk scoring, cross-border case escalation."},
            "applicable_to": ["reporting institutions"],
            "reporting_obligation": "Apply EDD; may require countermeasures or relationship termination",
            "penalty_range": "Non-compliance = regulatory breach",
            "tags": ["edd", "high_risk_country", "fatf", "cross_border", "correspondent_banking"],
            "is_active": True, "created_at": now, "updated_at": now,
        },
        {
            "rule_code": "POCAMLA-S46-RECORD-KEEPING",
            "act_name": "POCAMLA 2009 (Revised 2023) + POCAMLA Regulations 2023",
            "section": "Act s.46; Regulations 2023 reg.42",
            "title": "Record Keeping — 7-Year Retention",
            "summary": "Institutions must keep transaction records and CDD records with full identifying detail for at least 7 years and make them available to competent authorities.",
            "full_text": "Section 46 and Regulation 42 require retention of transaction and identity evidence for a minimum of 7 years, with timely access to competent authorities.",
            "rule_type": "reporting_obligation",
            "trigger_condition": {"scope": "all covered transactions and identity evidence", "retention_period": "at least 7 years"},
            "threshold_value": "7", "threshold_unit": "YEARS",
            "suspicion_indicators": ["missing records on request", "incomplete transaction evidence"],
            "case_type": "regulatory_report",
            "destination_body": ["FRC", "CBK"],
            "system_use": {"bank_side": "Retain full KYC, transaction metadata, correspondence, and investigation notes in immutable case-linked storage.", "frc_side": "Require document retention proof; retrieve transaction evidence, KYC files, and prior analysis during investigations."},
            "applicable_to": ["reporting institutions"],
            "reporting_obligation": "Retain records 7 years; make available on request",
            "penalty_range": "Up to KES 500,000 fine",
            "tags": ["record_keeping", "7_year_retention", "compliance", "data_retention"],
            "is_active": True, "created_at": now, "updated_at": now,
        },
        {
            "rule_code": "POCAMLA-S47-INTERNAL-REPORTING",
            "act_name": "POCAMLA 2009 (Revised 2023)",
            "section": "Section 47",
            "title": "Internal Reporting Procedures",
            "summary": "Institutions must maintain internal escalation procedures so employees can report suspicion to a responsible compliance officer who then decides whether to file with the Centre.",
            "full_text": "Section 47 requires institutions to have internal controls, an identified responsible officer, and escalation procedures. The officer must have access to all relevant information.",
            "rule_type": "reporting_obligation",
            "trigger_condition": {"event": "employee becomes aware of information causing suspicion"},
            "threshold_value": None, "threshold_unit": None,
            "suspicion_indicators": ["employee alert without compliance review trail"],
            "case_type": "regulatory_report",
            "destination_body": ["FRC"],
            "system_use": {"bank_side": "Employee referral portal, compliance review queue, approval-to-report workflow.", "frc_side": "Track whether institution had an internal escalation trail before filing the STR."},
            "applicable_to": ["reporting institutions"],
            "reporting_obligation": "Maintain internal reporting procedures; responsible officer must escalate",
            "penalty_range": "Breach = compliance failure",
            "tags": ["internal_reporting", "compliance_officer", "escalation", "procedures"],
            "is_active": True, "created_at": now, "updated_at": now,
        },
        {
            "rule_code": "POCAMLA-S47A-REGISTRATION",
            "act_name": "POCAMLA 2009 (Revised 2023) + POCAMLA Regulations 2023",
            "section": "Act s.47A; Regulations 2023 reg.5",
            "title": "Institution Registration with the Centre",
            "summary": "Every reporting institution must register with the Centre, keep registration updated, and report suspicious transactions even if registration is outstanding.",
            "full_text": "Section 47A and Regulation 5 require registration and change notification within 90 days. Failure to register is an offence.",
            "rule_type": "reporting_obligation",
            "trigger_condition": {"entity_status": "institution falls within reporting institution definition", "update_trigger": "change in registration particulars within 90 days"},
            "threshold_value": "90", "threshold_unit": "DAYS",
            "suspicion_indicators": ["unregistered institution attempting to submit"],
            "case_type": "regulatory_report",
            "destination_body": ["FRC"],
            "system_use": {"bank_side": "Use as institution onboarding rule and compliance status check.", "frc_side": "Build master registry, registration status, and non-registration enforcement list."},
            "applicable_to": ["all reporting institutions"],
            "reporting_obligation": "Register with FRC; update within 90 days of any change",
            "penalty_range": "Failure = offence",
            "tags": ["registration", "institution_registry", "compliance", "90_day_update"],
            "is_active": True, "created_at": now, "updated_at": now,
        },
        {
            "rule_code": "POCAMLA-S48-DNFBP-SCOPE",
            "act_name": "POCAMLA 2009 (Revised 2023)",
            "section": "Section 48",
            "title": "AML Obligations — Non-Bank Professionals (DNFBPs)",
            "summary": "AML reporting obligations extend to accountants, advocates, notaries, and trust/company service providers when they conduct specified financial transactions for clients.",
            "full_text": "Section 48 extends Part IV AML obligations to specified non-bank professionals including accountants, advocates, notaries, independent legal professionals, and TCSPs.",
            "rule_type": "reporting_obligation",
            "trigger_condition": {"entity_category": ["accountants", "advocates", "notaries", "independent legal professionals", "TCSPs"], "covered_activities": ["real estate buying/selling", "managing client money or assets", "bank/savings account management", "company creation/management", "buying/selling business entities"]},
            "threshold_value": None, "threshold_unit": None,
            "suspicion_indicators": ["high-value real estate transaction", "complex trust or company structure", "unusual asset management instruction"],
            "case_type": "regulatory_report",
            "destination_body": ["FRC", "CBK"],
            "system_use": {"bank_side": "Not a bank-only rule. Use to onboard non-bank institutions into the same reporting platform.", "frc_side": "Support multi-sector reporting portal and sector-specific workflows for legal professionals."},
            "applicable_to": ["accountants", "advocates", "notaries", "TCSPs"],
            "reporting_obligation": "Apply all AML obligations under Part IV; report where required",
            "penalty_range": "Same as for reporting institutions",
            "tags": ["dnfbp", "non_bank", "advocate", "accountant", "trust_company"],
            "is_active": True, "created_at": now, "updated_at": now,
        },
        {
            "rule_code": "POCAMLA-S44A-FRC-INTERVENTION",
            "act_name": "POCAMLA 2009 (Revised 2023)",
            "section": "Section 44A(1)-(2)",
            "title": "FRC No-Proceed / Transaction Intervention",
            "summary": "Where the Centre has reasonable grounds to suspect ML/TF/PF or property linked to a designated person, it may order a transaction not to proceed for up to 5 working days.",
            "full_text": "Section 44A empowers the FRC to issue a written no-proceed direction pausing a transaction for up to 5 working days to allow inquiry and referral.",
            "rule_type": "suspicious_activity_rule",
            "trigger_condition": {"frc_suspicion_basis": ["money laundering", "terrorism financing", "proliferation financing", "proceeds of crime", "designated person property"]},
            "threshold_value": "5", "threshold_unit": "WORKING_DAYS",
            "suspicion_indicators": ["active suspicious transaction under FRC review", "designated person link detected"],
            "case_type": "suspicious_activity_report",
            "destination_body": ["FRC", "DCI", "KRA"],
            "system_use": {"bank_side": "Support immediate hold/stop order execution and evidence preservation.", "frc_side": "Freeze/hold/no-proceed case-control module with expiry timer and audit trail."},
            "applicable_to": ["FRC", "reporting institutions"],
            "reporting_obligation": "FRC issues written direction; institution must comply within 5 working days",
            "penalty_range": "Non-compliance = criminal offence",
            "tags": ["intervention", "no_proceed", "hold_order", "5_day_timer", "frc_power"],
            "is_active": True, "created_at": now, "updated_at": now,
        },
        {
            "rule_code": "POTA-REG2023-FREEZE-ON-DESIGNATION",
            "act_name": "Prevention of Terrorism (UN SC Resolutions on Suppression of Terrorism) Regulations 2023",
            "section": "Regulations 2, 4, 6, 7",
            "title": "Terrorism Sanctions — Freeze on Designation (Without Delay)",
            "summary": "When a person or entity is designated under the terrorism sanctions framework, funds and property must be frozen without delay and without prior notice within 24 hours.",
            "full_text": "Regulations 2, 4, 6, and 7 define 'without delay' as within 24 hours. The designation list itself authorizes the freeze. No prior notice to the designated person is permitted.",
            "rule_type": "reporting_obligation",
            "trigger_condition": {"event": "designation or sanctions list circulated", "deadline": "within 24 hours"},
            "threshold_value": "24", "threshold_unit": "HOURS",
            "suspicion_indicators": ["sanctions list match", "designated entity linked account", "funds derived from designated person"],
            "case_type": "suspicious_activity_report",
            "destination_body": ["FRC", "ANTI_TERROR", "COMMITTEE"],
            "system_use": {"bank_side": "Real-time sanctions screening, immediate account freeze, block transactions, log match confidence.", "frc_side": "Receive freeze confirmations, monitor compliance timeliness, link designation events to suspicious transaction history."},
            "applicable_to": ["reporting institutions", "natural persons", "legal persons", "asset holders"],
            "reporting_obligation": "Freeze without delay (within 24 hours); no prior notice",
            "penalty_range": "Criminal offence for non-compliance",
            "tags": ["sanctions_freeze", "terrorism_financing", "24_hour_deadline", "designated_person", "no_prior_notice"],
            "is_active": True, "created_at": now, "updated_at": now,
        },
        {
            "rule_code": "POTA-REG2023-FREEZE-RETURNS",
            "act_name": "Prevention of Terrorism (UN SC Resolutions on Suppression of Terrorism) Regulations 2023",
            "section": "Regulation 30(1)-(3)",
            "title": "Post-Freeze Return and Attempted Dealing Report",
            "summary": "After a freeze, institutions must file a written return within 24 hours. Any attempted dealing with frozen property must also be reported within 24 hours.",
            "full_text": "Regulation 30 requires a detailed written return to the Cabinet Secretary and Centre within 24 hours of freeze. Attempted dealings must also be reported within 24 hours.",
            "rule_type": "reporting_obligation",
            "trigger_condition": {"events": ["receipt of freeze notice", "attempted dealing with frozen property"], "deadline": "within 24 hours"},
            "threshold_value": "24", "threshold_unit": "HOURS",
            "suspicion_indicators": ["attempted access to frozen account", "attempted transfer of frozen funds", "attempted withdrawal after freeze"],
            "case_type": "suspicious_activity_report",
            "destination_body": ["FRC", "COMMITTEE", "ANTI_TERROR", "DCI"],
            "system_use": {"bank_side": "Generate automated freeze-return pack with account details, holder, balance, and attempted access events.", "frc_side": "Sanctions-freeze reporting inbox and attempted-breach escalation workflow."},
            "applicable_to": ["reporting institutions", "relevant government agencies"],
            "reporting_obligation": "File written return within 24 hours; report attempted dealing within 24 hours",
            "penalty_range": "Non-compliance = criminal offence",
            "tags": ["sanctions_freeze", "post_freeze_return", "attempted_dealing", "24_hour_deadline"],
            "is_active": True, "created_at": now, "updated_at": now,
        },
        {
            "rule_code": "POTA-REG2023-SANCTIONS-MONITORING",
            "act_name": "Prevention of Terrorism (UN SC Resolutions on Suppression of Terrorism) Regulations 2023",
            "section": "Regulation 31",
            "title": "Ongoing Sanctions List Screening",
            "summary": "Institutions must regularly review domestic and sanctions lists and continuously monitor transactions involving listed entities to reduce terrorism financing risk.",
            "full_text": "Regulation 31 requires regular list review, ongoing customer screening, and transaction monitoring for entities on domestic and international sanctions lists.",
            "rule_type": "suspicious_activity_rule",
            "trigger_condition": {"monitoring_basis": ["domestic list", "UN sanctions list", "ongoing transactions involving listed entities"]},
            "threshold_value": None, "threshold_unit": None,
            "suspicion_indicators": ["sanctions list match in customer or beneficiary", "transaction linked to listed entity", "fuzzy name match requiring review"],
            "case_type": "suspicious_activity_report",
            "destination_body": ["FRC", "COMMITTEE", "ANTI_TERROR"],
            "system_use": {"bank_side": "Daily list refresh, customer screening, transaction screening, fuzzy name match review, linked-party detection.", "frc_side": "Supervise institutions on list freshness, match handling, and ongoing monitoring controls."},
            "applicable_to": ["reporting institutions"],
            "reporting_obligation": "Ongoing screening; report matches and suspicious transactions to FRC",
            "penalty_range": "Failure = terrorism financing compliance breach",
            "tags": ["sanctions_screening", "terrorism_financing", "ongoing_monitoring", "list_refresh"],
            "is_active": True, "created_at": now, "updated_at": now,
        },
        {
            "rule_code": "PF-REG2023-PROLIFERATION-SANCTIONS",
            "act_name": "Prevention of Terrorism (UN SC Resolutions on Proliferation Financing) Regulations 2023",
            "section": "Regulations 3, 4, 5",
            "title": "Proliferation Financing Sanctions — 24-Hour Implementation",
            "summary": "Proliferation-financing sanctions must be implemented within 24 hours of designation. The Committee Secretary must monitor lists daily and circulate designations electronically.",
            "full_text": "Regulations 3, 4, and 5 define 'without delay' as within 24 hours. Committee Secretary monitors sanctions lists daily. FRC, supervisory bodies, and self-regulatory bodies all have implementation roles.",
            "rule_type": "reporting_obligation",
            "trigger_condition": {"event": "UN designation under proliferation-financing sanctions regime", "deadline": "within 24 hours"},
            "threshold_value": "24", "threshold_unit": "HOURS",
            "suspicion_indicators": ["proliferation financing sanctions match", "transaction linked to designated state or entity"],
            "case_type": "regulatory_report",
            "destination_body": ["FRC", "COMMITTEE", "ANTI_TERROR"],
            "system_use": {"bank_side": "Treat proliferation-financing screening as a separate sanctions program from classic AML or TF screening.", "frc_side": "Dedicated proliferation-financing sanctions module with 24-hour compliance clock."},
            "applicable_to": ["FRC", "reporting institutions", "supervisory bodies", "Committee Secretary"],
            "reporting_obligation": "Implement within 24 hours; Committee Secretary circulates daily",
            "penalty_range": "Non-compliance = criminal offence",
            "tags": ["proliferation_financing", "pf_sanctions", "24_hour_deadline", "un_designation"],
            "is_active": True, "created_at": now, "updated_at": now,
        },
        {
            "rule_code": "PF-REG2023-COMPLIANCE-MONITORING",
            "act_name": "Prevention of Terrorism (Proliferation Financing) Regulations 2023",
            "section": "Regulation 12(1)-(3)",
            "title": "FRC Supervision of Proliferation Sanctions Compliance",
            "summary": "FRC, supervisory bodies, and self-regulatory bodies must monitor institutional compliance with proliferation sanctions, including list maintenance, screening, freezing, match reporting, and suspicious reporting.",
            "full_text": "Regulation 12 assigns supervisory roles to FRC, supervisory bodies, and SRBs. They must monitor list freshness, screening quality, false positives, freezing actions, positive name match reporting, and suspicious transactions on related accounts.",
            "rule_type": "reporting_obligation",
            "trigger_condition": {"compliance_scope": ["sanctions list maintenance", "customer screening", "false positive handling", "freezing/blocking", "positive name match", "related transactions"]},
            "threshold_value": None, "threshold_unit": None,
            "suspicion_indicators": ["institution failed to screen", "false positive mishandled", "delayed freeze action", "unreported positive match"],
            "case_type": "regulatory_report",
            "destination_body": ["FRC", "COMMITTEE"],
            "system_use": {"bank_side": "Require fields for positive-match reporting, false-positive resolution, related-party freeze logic, and suspicious-report linkage.", "frc_side": "Supervisory dashboards for screening quality, freeze action compliance, and report-submission completeness."},
            "applicable_to": ["FRC", "supervisory bodies", "self-regulatory bodies", "reporting institutions"],
            "reporting_obligation": "FRC monitors and can impose administrative sanctions",
            "penalty_range": "Administrative sanctions including fines",
            "tags": ["proliferation_financing", "supervisory_monitoring", "sanctions_compliance", "frc_supervision"],
            "is_active": True, "created_at": now, "updated_at": now,
        },
        {
            "rule_code": "PF-REG2023-DELISTING-UNFREEZING",
            "act_name": "Prevention of Terrorism (Proliferation Financing) Regulations 2023",
            "section": "Regulations 13-16",
            "title": "Delisting and Unfreezing of Assets",
            "summary": "Where a designated person is delisted or a mistaken freeze is confirmed, funds must be unfrozen without delay and delisting instructions must be respected.",
            "full_text": "Regulations 13-16 govern delisting procedures, unfreezing upon confirmed delisting, and processing applications where funds were frozen in error.",
            "rule_type": "reporting_obligation",
            "trigger_condition": {"events": ["confirmed delisting", "verified mistaken identity/erroneous freeze"]},
            "threshold_value": None, "threshold_unit": None,
            "suspicion_indicators": ["wrongful freeze confirmed", "delisting notice received"],
            "case_type": "regulatory_report",
            "destination_body": ["FRC", "COMMITTEE"],
            "system_use": {"bank_side": "Support sanctions lifecycle: freeze, review, delist, unfreeze, and mistaken-match correction.", "frc_side": "Delisting broadcast, unfreeze confirmation, and wrongful-freeze remediation workflow."},
            "applicable_to": ["reporting institutions", "persons holding targeted assets", "Committee"],
            "reporting_obligation": "Unfreeze without delay upon confirmed delisting; process error applications",
            "penalty_range": "Failure to unfreeze = regulatory breach",
            "tags": ["delisting", "unfreezing", "sanctions_lifecycle", "mistaken_freeze", "remediation"],
            "is_active": True, "created_at": now, "updated_at": now,
        },
    ]

    for rule in legal_rules:
        await upsert(db, "legal_rules", {"rule_code": rule["rule_code"]}, rule,
                     f"Rule {rule['rule_code']}: {rule['title']}")

    # ── Indexes ────────────────────────────────────────────────────────────────
    print("\nIndexes:")
    await db["users"].create_index("email", unique=True, background=True)
    await db["institutions"].create_index("institution_code", unique=True, background=True)
    await db["institutions"].create_index("api_key_hash", background=True)
    await db["cases"].create_index("frc_case_id", unique=True, background=True)
    await db["cases"].create_index([("institution_id", 1), ("status", 1)], background=True)
    await db["legal_rules"].create_index("rule_code", unique=True, background=True)
    await db["legal_rules"].create_index("tags", background=True)
    await db["legal_rules"].create_index("rule_type", background=True)
    await db["legal_rules"].create_index("case_type", background=True)
    await db["reports"].create_index("report_id", unique=True, background=True)
    await db["reports"].create_index("frc_case_id", background=True)
    await db["referrals"].create_index("referral_id", unique=True, background=True)
    await db["referrals"].create_index("frc_case_id", background=True)
    await db["referrals"].create_index("destination_body", background=True)
    await db["audit_logs"].create_index([("timestamp", -1)], background=True)
    print("  [OK]   All indexes verified")

    client.close()
    print(f"\n{'='*60}")
    print("Seed complete.")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    asyncio.run(seed())
