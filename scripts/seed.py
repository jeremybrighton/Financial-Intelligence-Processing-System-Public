"""
FRC System — Database Seed Script
====================================
Creates:
  1. FRC admin user
  2. FRC analyst user
  3. Demo institution (FraudGuard Bank)
  4. Institution API key (printed once — save it)
  5. 5 seed legal rules (POCAMLA-derived)

Run from project root:
  MONGODB_URI=<uri> JWT_SECRET_KEY=<any> python scripts/seed.py

Set RESET=true to wipe and re-seed existing records.
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

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

MONGO_URI = os.environ.get("MONGODB_URI")
DB_NAME   = os.environ.get("MONGODB_DB_NAME", "frc_db")
RESET     = os.environ.get("RESET", "false").lower() == "true"

if not MONGO_URI:
    raise ValueError("MONGODB_URI environment variable is required")


async def upsert(db, collection: str, filter_: dict, doc: dict, label: str):
    existing = await db[collection].find_one(filter_)
    if existing and not RESET:
        print(f"  [SKIP] {label} already exists")
        return existing["_id"]
    if existing:
        await db[collection].delete_one(filter_)
    result = await db[collection].insert_one(doc)
    print(f"  [OK]   {label}")
    return result.inserted_id


async def seed():
    print(f"\n{'='*58}")
    print("Financial Intelligence Processing System — Seed")
    print(f"Database: {DB_NAME}  |  RESET={RESET}")
    print(f"{'='*58}\n")

    client = AsyncIOMotorClient(MONGO_URI, server_api=ServerApi("1"), tls=True)
    db = client[DB_NAME]
    now = datetime.now(timezone.utc)

    # ── Users ──────────────────────────────────────────────────────────────────
    print("Users:")
    await upsert(db, "users", {"email": "admin@frc.go.ke"}, {
        "email": "admin@frc.go.ke",
        "full_name": "FRC System Administrator",
        "password_hash": pwd.hash("FRCAdmin2026!"),
        "role": "frc_admin", "is_active": True,
        "last_login": None, "created_at": now, "updated_at": now,
    }, "admin@frc.go.ke  /  FRCAdmin2026!")

    await upsert(db, "users", {"email": "analyst@frc.go.ke"}, {
        "email": "analyst@frc.go.ke",
        "full_name": "Demo FRC Analyst",
        "password_hash": pwd.hash("FRCAnalyst2026!"),
        "role": "frc_analyst", "is_active": True,
        "last_login": None, "created_at": now, "updated_at": now,
    }, "analyst@frc.go.ke  /  FRCAnalyst2026!")

    await upsert(db, "users", {"email": "investigator@frc.go.ke"}, {
        "email": "investigator@frc.go.ke",
        "full_name": "Demo Investigator",
        "password_hash": pwd.hash("FRCInvest2026!"),
        "role": "investigator", "is_active": True,
        "last_login": None, "created_at": now, "updated_at": now,
    }, "investigator@frc.go.ke  /  FRCInvest2026!")

    # ── Institution ────────────────────────────────────────────────────────────
    print("\nInstitutions:")
    inst_code = "FRAUDGUARD-BANK"
    inst_existing = await db["institutions"].find_one({"institution_code": inst_code})

    if inst_existing and not RESET:
        print(f"  [SKIP] Institution {inst_code} already exists")
        inst_id = inst_existing["_id"]
        has_key = bool(inst_existing.get("api_key_hash"))
    else:
        if inst_existing:
            await db["institutions"].delete_one({"institution_code": inst_code})
        result = await db["institutions"].insert_one({
            "institution_code": inst_code,
            "institution_name": "FraudGuard Demo Bank",
            "institution_type": "commercial_bank",
            "supervisory_body": "Central Bank of Kenya",
            "contact_email": "compliance@fraudguard.bank",
            "status": "active", "is_active": True,
            "api_key_hash": None, "api_key_suffix": None,
            "submission_count": 0, "created_at": now, "updated_at": now,
        })
        inst_id = result.inserted_id
        has_key = False
        print(f"  [OK]   Institution: {inst_code}")

    # ── API key ────────────────────────────────────────────────────────────────
    if not has_key or RESET:
        alphabet = string.ascii_letters + string.digits
        raw_key  = "frc_" + "".join(secrets.choice(alphabet) for _ in range(48))
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        suffix   = raw_key[-6:]
        await db["institutions"].update_one(
            {"_id": inst_id},
            {"$set": {"api_key_hash": key_hash, "api_key_suffix": suffix, "updated_at": now}},
        )
        print(f"\n  {'!'*54}")
        print(f"  Institution API Key for {inst_code}:")
        print(f"\n  {raw_key}\n")
        print(f"  Add to FraudGuard / ML backend environment:")
        print(f"  FRC_API_KEY={raw_key}")
        print(f"  FRC_INTAKE_URL=https://<render-url>/api/v1/intake/cases")
        print(f"\n  SAVE THIS KEY — shown only once.")
        print(f"  {'!'*54}\n")

    # ── Legal rules ────────────────────────────────────────────────────────────
    print("Legal Rules:")
    legal_rules = [
        {
            "rule_code": "POCAMLA-S13",
            "title": "Duty to Report Suspicious Transactions",
            "source_document": "Proceeds of Crime and Anti-Money Laundering Act (POCAMLA) 2009",
            "section": "Section 13",
            "summary": "Every reporting institution must report suspicious transactions to the FRC as soon as possible.",
            "full_text": "Every reporting institution shall, as soon as practicable after forming a suspicion that a transaction is suspicious, report the transaction to the Centre.",
            "applicable_to": ["money_laundering", "terrorist_financing", "fraud"],
            "reporting_obligation": "Report to FRC immediately on suspicion",
            "penalty_range": "Up to KES 5,000,000 fine or 5 years imprisonment",
            "tags": ["suspicious_activity", "mandatory_reporting", "sar"],
            "is_active": True, "created_at": now, "updated_at": now,
        },
        {
            "rule_code": "POCAMLA-S14",
            "title": "Cash Transaction Reports",
            "source_document": "Proceeds of Crime and Anti-Money Laundering Act (POCAMLA) 2009",
            "section": "Section 14",
            "summary": "Reporting institutions must file cash transaction reports for transactions exceeding prescribed thresholds.",
            "full_text": "Every reporting institution shall report to the Centre every cash transaction exceeding the prescribed threshold in a single business day.",
            "applicable_to": ["money_laundering", "tax_evasion"],
            "reporting_obligation": "File CTR — threshold triggers mandatory report without suspicion",
            "penalty_range": "Up to KES 1,000,000 fine",
            "tags": ["ctr", "cash_transaction", "threshold", "mandatory_reporting"],
            "is_active": True, "created_at": now, "updated_at": now,
        },
        {
            "rule_code": "POCAMLA-S16",
            "title": "Tipping Off Prohibited",
            "source_document": "Proceeds of Crime and Anti-Money Laundering Act (POCAMLA) 2009",
            "section": "Section 16",
            "summary": "It is an offence to disclose to any person that a report has been made or that an investigation is underway.",
            "full_text": "A person shall not disclose to any other person that a report has been made or that an investigation is being conducted.",
            "applicable_to": ["money_laundering", "obstruction_of_justice"],
            "reporting_obligation": "Prohibits tipping off — strict confidentiality required",
            "penalty_range": "Up to KES 5,000,000 fine or 3 years imprisonment",
            "tags": ["tipping_off", "confidentiality", "investigation"],
            "is_active": True, "created_at": now, "updated_at": now,
        },
        {
            "rule_code": "POCAMLA-S17",
            "title": "Record Keeping",
            "source_document": "Proceeds of Crime and Anti-Money Laundering Act (POCAMLA) 2009",
            "section": "Section 17",
            "summary": "Reporting institutions must keep transaction records for a minimum of 7 years.",
            "full_text": "Every reporting institution shall keep records of all transactions for a period of not less than seven years.",
            "applicable_to": ["money_laundering", "compliance"],
            "reporting_obligation": "Retain records for 7 years minimum",
            "penalty_range": "Up to KES 500,000 fine",
            "tags": ["record_keeping", "7_year_retention", "compliance"],
            "is_active": True, "created_at": now, "updated_at": now,
        },
        {
            "rule_code": "POCAMLA-S21",
            "title": "Cross-Border Currency Movement",
            "source_document": "Proceeds of Crime and Anti-Money Laundering Act (POCAMLA) 2009",
            "section": "Section 21",
            "summary": "Persons transporting currency above the prescribed threshold across borders must declare it.",
            "full_text": "Any person who imports or exports currency or bearer negotiable instruments exceeding the prescribed threshold shall declare the amount to the relevant authority.",
            "applicable_to": ["money_laundering", "capital_flight", "tax_evasion"],
            "reporting_obligation": "Declaration required — institution must report facilitating transactions",
            "penalty_range": "Seizure of funds; up to KES 2,000,000 fine",
            "tags": ["cross_border", "cbt", "threshold", "declaration"],
            "is_active": True, "created_at": now, "updated_at": now,
        },
    ]

    for rule in legal_rules:
        await upsert(
            db, "legal_rules", {"rule_code": rule["rule_code"]},
            rule, f"Rule {rule['rule_code']}: {rule['title']}"
        )

    # ── Indexes ────────────────────────────────────────────────────────────────
    print("\nIndexes:")
    await db["users"].create_index("email", unique=True, background=True)
    await db["institutions"].create_index("institution_code", unique=True, background=True)
    await db["institutions"].create_index("api_key_hash", background=True)
    await db["cases"].create_index("frc_case_id", unique=True, background=True)
    await db["cases"].create_index([("institution_id",1),("status",1)], background=True)
    await db["legal_rules"].create_index("rule_code", unique=True, background=True)
    await db["legal_rules"].create_index("tags", background=True)
    await db["reports"].create_index("report_id", unique=True, background=True)
    await db["reports"].create_index("frc_case_id", background=True)
    await db["referrals"].create_index("referral_id", unique=True, background=True)
    await db["referrals"].create_index("frc_case_id", background=True)
    await db["audit_logs"].create_index([("timestamp",-1)], background=True)
    print("  [OK]   All indexes verified")

    client.close()
    print(f"\n{'='*58}")
    print("Seed complete.")
    print(f"{'='*58}\n")


if __name__ == "__main__":
    asyncio.run(seed())
