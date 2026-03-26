"""
FRC System — MongoDB Connection (async Motor client)
Targets frc_db — completely separate from fraudguard's fraud_detection db.
"""

import logging
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.server_api import ServerApi
from backend.core.config import settings

log = logging.getLogger(__name__)
_client = None


def get_client():
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(settings.MONGO_URI, server_api=ServerApi("1"), tls=True)
    return _client


def get_db():
    return get_client()[settings.FRC_DB_NAME]


def users_col():            return get_db()["users"]
def institutions_col():     return get_db()["institutions"]
def api_keys_col():         return get_db()["institution_api_keys"]
def policy_rules_col():     return get_db()["policy_rules"]
def case_submissions_col(): return get_db()["case_submissions"]
def frc_cases_col():        return get_db()["frc_cases"]
def case_timeline_col():    return get_db()["case_timeline"]
def case_notes_col():       return get_db()["case_notes"]
def case_evidence_col():    return get_db()["case_evidence"]
def legal_provisions_col(): return get_db()["legal_provisions"]
def report_templates_col(): return get_db()["report_templates"]
def case_reports_col():     return get_db()["case_reports"]
def referrals_col():        return get_db()["referrals"]
def audit_logs_col():       return get_db()["audit_logs"]
def notifications_col():    return get_db()["notifications"]
def refresh_tokens_col():   return get_db()["refresh_tokens"]


async def create_indexes():
    db = get_db()
    await db["users"].create_index("email", unique=True, background=True)
    await db["institutions"].create_index("institution_code", unique=True, background=True)
    await db["institution_api_keys"].create_index("key_hash", unique=True, background=True)
    await db["institution_api_keys"].create_index("institution_id", background=True)
    await db["policy_rules"].create_index("rule_code", unique=True, background=True)
    await db["case_submissions"].create_index("institution_id", background=True)
    await db["frc_cases"].create_index("case_number", unique=True, background=True)
    await db["frc_cases"].create_index("status", background=True)
    await db["frc_cases"].create_index("institution_id", background=True)
    await db["frc_cases"].create_index("created_at", background=True)
    await db["case_timeline"].create_index("case_id", background=True)
    await db["case_notes"].create_index("case_id", background=True)
    await db["case_evidence"].create_index("case_id", background=True)
    await db["legal_provisions"].create_index("provision_id", unique=True, background=True)
    await db["legal_provisions"].create_index("tags", background=True)
    await db["report_templates"].create_index("template_code", unique=True, background=True)
    await db["case_reports"].create_index("case_id", background=True)
    await db["referrals"].create_index("case_id", background=True)
    await db["audit_logs"].create_index("timestamp", background=True)
    await db["audit_logs"].create_index("actor_id", background=True)
    await db["refresh_tokens"].create_index("token_hash", unique=True, background=True)
    await db["refresh_tokens"].create_index("expires_at", expireAfterSeconds=0, background=True)
    log.info("MongoDB indexes created/verified.")


async def ping_db():
    try:
        await get_client().admin.command("ping")
        log.info("MongoDB connection verified.")
        return True
    except Exception as e:
        log.error(f"MongoDB ping failed: {e}")
        return False
