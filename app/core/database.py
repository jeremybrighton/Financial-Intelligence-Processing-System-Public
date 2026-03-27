"""
FRC System — MongoDB Connection
=================================
Async Motor client targeting frc_db.
Completely separate from the FraudGuard / ML backend database.

Collections:
  users, institutions, cases, legal_rules, reports, referrals, audit_logs
"""
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.server_api import ServerApi
from app.core.config import settings

log = logging.getLogger(__name__)

_client: AsyncIOMotorClient | None = None


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(
            settings.MONGODB_URI,
            server_api=ServerApi("1"),
            tls=True,
        )
    return _client


def get_db():
    return get_client()[settings.MONGODB_DB_NAME]


# ── Collection accessors ──────────────────────────────────────────────────────

def users_col():        return get_db()["users"]
def institutions_col(): return get_db()["institutions"]
def cases_col():        return get_db()["cases"]
def legal_rules_col():  return get_db()["legal_rules"]
def reports_col():      return get_db()["reports"]
def referrals_col():    return get_db()["referrals"]
def audit_logs_col():   return get_db()["audit_logs"]


async def create_indexes():
    """Create MongoDB indexes on startup. Idempotent — safe to call every time."""
    db = get_db()

    # users
    await db["users"].create_index("email", unique=True, background=True)
    await db["users"].create_index("role", background=True)

    # institutions
    await db["institutions"].create_index("institution_code", unique=True, background=True)
    await db["institutions"].create_index("status", background=True)
    await db["institutions"].create_index("api_key_hash", background=True)

    # cases
    await db["cases"].create_index("frc_case_id", unique=True, background=True)
    await db["cases"].create_index("institution_id", background=True)
    await db["cases"].create_index("status", background=True)
    await db["cases"].create_index("report_type", background=True)
    await db["cases"].create_index("priority", background=True)
    await db["cases"].create_index("created_at", background=True)

    # legal_rules
    await db["legal_rules"].create_index("rule_code", unique=True, background=True)
    await db["legal_rules"].create_index("tags", background=True)
    await db["legal_rules"].create_index("applicable_to", background=True)
    await db["legal_rules"].create_index("is_active", background=True)

    # reports
    await db["reports"].create_index("report_id", unique=True, background=True)
    await db["reports"].create_index("frc_case_id", background=True)
    await db["reports"].create_index("status", background=True)

    # referrals
    await db["referrals"].create_index("referral_id", unique=True, background=True)
    await db["referrals"].create_index("frc_case_id", background=True)
    await db["referrals"].create_index("status", background=True)
    await db["referrals"].create_index("referred_to", background=True)

    # audit_logs
    await db["audit_logs"].create_index("user_id", background=True)
    await db["audit_logs"].create_index("action", background=True)
    await db["audit_logs"].create_index("module", background=True)
    await db["audit_logs"].create_index("timestamp", background=True)

    log.info("MongoDB indexes created/verified.")


async def ping_db() -> bool:
    try:
        await get_client().admin.command("ping")
        log.info("MongoDB connection verified.")
        return True
    except Exception as e:
        log.error(f"MongoDB ping failed: {e}")
        return False
