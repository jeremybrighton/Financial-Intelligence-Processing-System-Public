"""
FRC System — Database Seed Script
Run: MONGO_URI=<uri> SECRET_KEY=any python scripts/seed_db.py
"""
import asyncio, json, os, sys, hashlib, secrets, string
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.server_api import ServerApi
from passlib.context import CryptContext

MONGO_URI = os.environ.get("MONGO_URI")
if not MONGO_URI: raise ValueError("MONGO_URI required")
DB_NAME = os.environ.get("FRC_DB_NAME", "frc_db")
RESET = os.environ.get("RESET_DEMO", "false").lower() == "true"

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
def _hash_pw(p): return pwd.hash(p)
def _gen_key(n=48):
    a=string.ascii_letters+string.digits; raw="".join(secrets.choice(a) for _ in range(n)); return f"frc_{raw}"
def _hash_key(k): return hashlib.sha256(k.encode()).hexdigest()

async def seed():
    print(f"\n{'='*50}\nFRC System — Seed\nDB: {DB_NAME}\n{'='*50}")
    client = AsyncIOMotorClient(MONGO_URI, server_api=ServerApi("1"), tls=True)
    db = client[DB_NAME]; now = datetime.now(timezone.utc)

    # Admin user
    admin_email="admin@frc.gov.mu"; admin_pw="FRC@Admin2026!"
    if not await db["users"].find_one({"email":admin_email}) or RESET:
        await db["users"].delete_one({"email":admin_email})
        r=await db["users"].insert_one({"email":admin_email,"full_name":"FRC Administrator","password_hash":_hash_pw(admin_pw),"role":"frc_admin","is_active":True,"created_at":now,"updated_at":now})
        print(f"[OK] Admin: {admin_email} / {admin_pw} (id: {r.inserted_id})")
    else: print(f"[SKIP] Admin exists")

    # Demo analyst
    analyst_email="analyst@frc.gov.mu"
    if not await db["users"].find_one({"email":analyst_email}) or RESET:
        await db["users"].delete_one({"email":analyst_email})
        await db["users"].insert_one({"email":analyst_email,"full_name":"Demo Analyst","password_hash":_hash_pw("Analyst@2026!"),"role":"frc_analyst","is_active":True,"created_at":now,"updated_at":now})
        print(f"[OK] Analyst: {analyst_email} / Analyst@2026!")
    else: print(f"[SKIP] Analyst exists")

    # Demo institution
    inst_code="FRAUDGUARD-BANK"
    existing_inst=await db["institutions"].find_one({"institution_code":inst_code})
    if not existing_inst or RESET:
        await db["institutions"].delete_one({"institution_code":inst_code})
        r=await db["institutions"].insert_one({"institution_code":inst_code,"name":"FraudGuard Demo Bank","institution_type":"commercial_bank","licence_number":"MU-BANK-2024-001","country":"MU","contact_email":"compliance@fraudguard.mu","contact_name":"Head of Compliance","is_active":True,"status":"active","submitted_case_count":0,"registration_date":now,"created_at":now,"updated_at":now})
        inst_id=str(r.inserted_id); print(f"[OK] Institution: {inst_code} (id: {inst_id})")
    else:
        inst_id=str(existing_inst["_id"]); print(f"[SKIP] Institution exists")

    # API key
    if not await db["institution_api_keys"].find_one({"institution_id":inst_id,"is_active":True}) or RESET:
        await db["institution_api_keys"].delete_many({"institution_id":inst_id})
        raw_key=_gen_key()
        await db["institution_api_keys"].insert_one({"institution_id":inst_id,"key_hash":_hash_key(raw_key),"key_prefix":raw_key[-6:],"label":"FraudGuard Production","is_active":True,"expires_at":None,"last_used_at":None,"created_by":"seed","created_at":now,"updated_at":now})
        print(f"\n{'!'*50}")
        print(f"[OK] API Key: {raw_key}")
        print(f"     Set in ML backend: FRC_API_KEY={raw_key}")
        print(f"{'!'*50}\n")
    else: print(f"[SKIP] API key exists")

    # Policy rules
    rules=[
        {"rule_code":"CTR_15000","name":"Cash Transaction Report — USD 15,000","description":"Mandatory CTR for cash >= USD 15,000 (POCAMLA S.14)","rule_type":"threshold_amount","submission_type":"regulatory_report","is_active":True,"priority":10,"conditions":{"min_amount_usd":15000},"legal_basis":"POCAMLA 2012 Section 14(1)","created_at":now,"updated_at":now},
        {"rule_code":"CBT_10000","name":"Cross-Border Transfer >= USD 10,000","description":"Mandatory CBT report (POCAMLA S.15)","rule_type":"cross_border","submission_type":"regulatory_report","is_active":True,"priority":20,"conditions":{"min_amount_usd":10000},"legal_basis":"POCAMLA 2012 Section 15","created_at":now,"updated_at":now},
        {"rule_code":"SAR_ML_70","name":"SAR — ML Score >= 0.70","description":"Suspicious Activity Report on ML score >= 70%","rule_type":"ml_score","submission_type":"suspicious_activity_report","is_active":True,"priority":30,"conditions":{"min_score":0.70},"legal_basis":"POCAMLA 2012 Section 13","created_at":now,"updated_at":now},
        {"rule_code":"SAR_TX_TYPE","name":"SAR — High-risk tx types","description":"SAR for TRANSFER and CASH_OUT types","rule_type":"transaction_type","submission_type":"suspicious_activity_report","is_active":True,"priority":40,"conditions":{"types":["TRANSFER","CASH_OUT"]},"legal_basis":"POCAMLA 2012 Section 13","created_at":now,"updated_at":now},
    ]
    for rule in rules:
        if not await db["policy_rules"].find_one({"rule_code":rule["rule_code"]}) or RESET:
            await db["policy_rules"].delete_one({"rule_code":rule["rule_code"]})
            await db["policy_rules"].insert_one(rule); print(f"[OK] Rule: {rule['rule_code']}")
        else: print(f"[SKIP] Rule {rule['rule_code']} exists")

    # STR Template
    tmpl_code="STR_V1"
    if not await db["report_templates"].find_one({"template_code":tmpl_code}) or RESET:
        await db["report_templates"].delete_one({"template_code":tmpl_code})
        await db["report_templates"].insert_one({"template_code":tmpl_code,"name":"Suspicious Transaction Report (STR)","description":"Standard FRC STR aligned with POCAMLA","report_type":"str","sections":[{"section_key":"reporting_institution","section_title":"Reporting Institution","description":"Name, licence, contact","required":True,"field_type":"text"},{"section_key":"subject_details","section_title":"Subject Details","description":"Name, ID, account","required":True,"field_type":"text"},{"section_key":"transaction_details","section_title":"Transaction Details","description":"Date, amount, channel","required":True,"field_type":"text"},{"section_key":"suspicion_indicators","section_title":"Grounds for Suspicion","description":"Why suspicious","required":True,"field_type":"text"},{"section_key":"legal_provisions","section_title":"Legal Provisions","description":"Applicable POCAMLA/FIAMLA sections","required":True,"field_type":"list"},{"section_key":"recommended_action","section_title":"Recommended Action","description":"Referral recommendation","required":True,"field_type":"text"},{"section_key":"analyst_declaration","section_title":"Analyst Declaration","description":"Analyst sign-off","required":True,"field_type":"text"}],"required_fields":["reporting_institution","subject_details","transaction_details","suspicion_indicators","legal_provisions","recommended_action","analyst_declaration"],"legal_provision_tags":["suspicious_activity","mandatory_reporting"],"is_active":True,"version":"1.0","created_at":now,"updated_at":now})
        print(f"[OK] Template: {tmpl_code}")
    else: print(f"[SKIP] Template {tmpl_code} exists")

    # Legal KB
    legal_file=Path(__file__).parent.parent/"legal"/"structured"/"seed_legal_kb.json"
    if legal_file.exists():
        with open(legal_file) as f: provisions=json.load(f)
        count=0
        for p in provisions:
            if not await db["legal_provisions"].find_one({"provision_id":p["provision_id"]}) or RESET:
                await db["legal_provisions"].delete_one({"provision_id":p["provision_id"]})
                p["created_at"]=now; p["updated_at"]=now
                await db["legal_provisions"].insert_one(p); count+=1
        print(f"[OK] Legal provisions: {count} inserted")
    else: print(f"[WARN] legal/structured/seed_legal_kb.json not found")

    # Indexes
    await db["users"].create_index("email",unique=True,background=True)
    await db["institutions"].create_index("institution_code",unique=True,background=True)
    await db["institution_api_keys"].create_index("key_hash",unique=True,background=True)
    await db["policy_rules"].create_index("rule_code",unique=True,background=True)
    await db["frc_cases"].create_index("case_number",unique=True,background=True)
    await db["legal_provisions"].create_index("provision_id",unique=True,background=True)
    await db["report_templates"].create_index("template_code",unique=True,background=True)
    print("[OK] Indexes verified")

    client.close()
    print(f"\n{'='*50}\nSeed complete.\n{'='*50}")

if __name__=="__main__":
    asyncio.run(seed())
