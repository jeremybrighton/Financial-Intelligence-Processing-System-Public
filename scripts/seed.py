"""
FRC System — Database Seed Script
====================================
Creates:
  1. One FRC admin user
  2. One FRC analyst user
  3. One demo institution (FraudGuard Bank)
  4. API key for the demo institution

Run from project root:
  MONGODB_URI=<uri> JWT_SECRET_KEY=<any> python scripts/seed.py

On success, prints the generated institution API key.
Save it — it is shown only once.
"""

import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.server_api import ServerApi
from passlib.context import CryptContext

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

MONGO_URI = os.environ.get("MONGODB_URI")
DB_NAME = os.environ.get("MONGODB_DB_NAME", "frc_db")

if not MONGO_URI:
    raise ValueError("MONGODB_URI environment variable is required")


async def seed():
    print(f"\n{'='*55}")
    print("FRC System — Database Seed")
    print(f"Database: {DB_NAME}")
    print(f"{'='*55}\n")

    client = AsyncIOMotorClient(MONGO_URI, server_api=ServerApi("1"), tls=True)
    db = client[DB_NAME]
    now = datetime.now(timezone.utc)

    # ── Admin user ─────────────────────────────────────────────────────────────
    admin_email = "admin@frc.go.ke"
    admin_pw = "FRCAdmin2026!"
    existing = await db["users"].find_one({"email": admin_email})
    if existing:
        print(f"[SKIP] Admin already exists: {admin_email}")
    else:
        await db["users"].insert_one({
            "email": admin_email,
            "full_name": "FRC System Administrator",
            "password_hash": pwd.hash(admin_pw),
            "role": "frc_admin",
            "is_active": True,
            "last_login": None,
            "created_at": now,
            "updated_at": now,
        })
        print(f"[OK] Admin user created")
        print(f"     Email:    {admin_email}")
        print(f"     Password: {admin_pw}")

    # ── Analyst user ───────────────────────────────────────────────────────────
    analyst_email = "analyst@frc.go.ke"
    analyst_pw = "FRCAnalyst2026!"
    existing = await db["users"].find_one({"email": analyst_email})
    if existing:
        print(f"[SKIP] Analyst already exists: {analyst_email}")
    else:
        await db["users"].insert_one({
            "email": analyst_email,
            "full_name": "Demo FRC Analyst",
            "password_hash": pwd.hash(analyst_pw),
            "role": "frc_analyst",
            "is_active": True,
            "last_login": None,
            "created_at": now,
            "updated_at": now,
        })
        print(f"[OK] Analyst created: {analyst_email} / {analyst_pw}")

    # ── Demo institution ───────────────────────────────────────────────────────
    inst_code = "FRAUDGUARD-BANK"
    existing_inst = await db["institutions"].find_one({"institution_code": inst_code})
    if existing_inst:
        print(f"[SKIP] Institution already exists: {inst_code}")
        inst_id = existing_inst["_id"]
    else:
        result = await db["institutions"].insert_one({
            "institution_code": inst_code,
            "institution_name": "FraudGuard Demo Bank",
            "institution_type": "commercial_bank",
            "supervisory_body": "Central Bank of Kenya",
            "contact_email": "compliance@fraudguard.bank",
            "status": "active",
            "is_active": True,
            "api_key_hash": None,
            "api_key_suffix": None,
            "submission_count": 0,
            "created_at": now,
            "updated_at": now,
        })
        inst_id = result.inserted_id
        print(f"[OK] Institution created: {inst_code}")

    # ── Generate API key ───────────────────────────────────────────────────────
    import hashlib, secrets, string
    existing_key = await db["institutions"].find_one({
        "_id": inst_id, "api_key_hash": {"$ne": None}
    })
    if existing_key and existing_key.get("api_key_hash"):
        print(f"[SKIP] API key already exists for {inst_code}")
    else:
        alphabet = string.ascii_letters + string.digits
        raw_key = "frc_" + "".join(secrets.choice(alphabet) for _ in range(48))
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        key_suffix = raw_key[-6:]
        await db["institutions"].update_one(
            {"_id": inst_id},
            {"$set": {
                "api_key_hash": key_hash,
                "api_key_suffix": key_suffix,
                "updated_at": now,
            }},
        )
        print(f"\n{'!'*55}")
        print(f"[OK] Institution API Key generated for {inst_code}")
        print(f"\n     API_KEY: {raw_key}")
        print(f"\n     Add this to FraudGuard (ML backend) environment:")
        print(f"     FRC_API_KEY={raw_key}")
        print(f"     FRC_INTAKE_URL=https://<your-render-url>/api/v1/intake/cases")
        print(f"\n     SAVE THIS KEY — it will not be shown again.")
        print(f"{'!'*55}\n")

    # ── Indexes ────────────────────────────────────────────────────────────────
    await db["users"].create_index("email", unique=True, background=True)
    await db["institutions"].create_index("institution_code", unique=True, background=True)
    await db["institutions"].create_index("api_key_hash", background=True)
    await db["cases"].create_index("frc_case_id", unique=True, background=True)
    await db["cases"].create_index("institution_id", background=True)
    await db["cases"].create_index("status", background=True)
    await db["audit_logs"].create_index("timestamp", background=True)
    print("[OK] Indexes verified")

    client.close()
    print(f"\n{'='*55}")
    print("Seed complete.")
    print(f"{'='*55}\n")


if __name__ == "__main__":
    asyncio.run(seed())
