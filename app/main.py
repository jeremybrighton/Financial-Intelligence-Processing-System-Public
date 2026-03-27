"""
Financial Intelligence Processing System — FastAPI Entry Point
================================================================
FRC-side backend platform.

Local dev:
  uvicorn app.main:app --reload --port 8000

Production (Render):
  Procfile → uvicorn app.main:app --host 0.0.0.0 --port $PORT
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import create_indexes, ping_db
from app.core.exceptions import register_exception_handlers
from app.routers import audit, auth, cases, health, institutions, intake, users

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger(__name__)

# ── App ────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "FRC-side platform for receiving institution case submissions, "
        "managing FRC cases, institutions, legal mappings, reports, and referrals."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# ── CORS ───────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Institution-API-Key"],
)

# ── Exception handlers ─────────────────────────────────────────────────────────
register_exception_handlers(app)

# ── Startup ────────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def on_startup():
    log.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION} [{settings.ENVIRONMENT}]")
    if await ping_db():
        await create_indexes()
        log.info("Database ready.")
    else:
        log.warning("Database unreachable on startup — will retry on first request.")


@app.on_event("shutdown")
async def on_shutdown():
    from app.core.database import get_client
    try:
        get_client().close()
        log.info("MongoDB connection closed.")
    except Exception:
        pass


# ── Routers ────────────────────────────────────────────────────────────────────
# Health — no prefix (root level)
app.include_router(health.router)

# All other routes under /api/v1
PREFIX = settings.API_V1_PREFIX
app.include_router(auth.router,         prefix=PREFIX)
app.include_router(users.router,        prefix=PREFIX)
app.include_router(institutions.router, prefix=PREFIX)
app.include_router(intake.router,       prefix=PREFIX)
app.include_router(cases.router,        prefix=PREFIX)
app.include_router(audit.router,        prefix=PREFIX)


# Future routers (not yet implemented — listed here for clarity):
# from app.routers import legal, reports, referrals
# app.include_router(legal.router,    prefix=PREFIX)
# app.include_router(reports.router,  prefix=PREFIX)
# app.include_router(referrals.router, prefix=PREFIX)
