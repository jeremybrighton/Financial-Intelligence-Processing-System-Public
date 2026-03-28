"""
Financial Intelligence Processing System — FastAPI Entry Point
FRC-side backend. Hosted on Render.

Local dev:    uvicorn app.main:app --reload --port 8000
Production:   Procfile → uvicorn app.main:app --host 0.0.0.0 --port $PORT
API docs:     http://localhost:8000/docs
"""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import create_indexes, ping_db
from app.core.exceptions import register_exception_handlers
from app.routers import (
    audit,
    auth,
    cases,
    health,
    institutions,
    intake,
    legal,
    referrals,
    reports,
    setup,
    users,
)

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger(__name__)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "FRC-side platform — receives institution case submissions, manages FRC cases, "
        "institutions, POCAMLA legal rules, reports, referrals to DCI/KRA/CBK/EACC/NIS/ARA/Egmont, "
        "and audit logs."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS — origins set via environment variable
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Institution-API-Key"],
)

register_exception_handlers(app)


@app.on_event("startup")
async def on_startup():
    log.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION} [{settings.ENVIRONMENT}]")
    if await ping_db():
        await create_indexes()
        log.info("Database ready.")
    else:
        log.warning("Database unreachable on startup — check MONGODB_URI.")


@app.on_event("shutdown")
async def on_shutdown():
    from app.core.database import get_client
    try:
        get_client().close()
    except Exception:
        pass


# Health endpoints — no versioned prefix
app.include_router(health.router)

PREFIX = settings.API_V1_PREFIX    # /api/v1

app.include_router(auth.router,         prefix=PREFIX)
app.include_router(users.router,        prefix=PREFIX)
app.include_router(institutions.router, prefix=PREFIX)
app.include_router(intake.router,       prefix=PREFIX)
app.include_router(cases.router,        prefix=PREFIX)
app.include_router(legal.router,        prefix=PREFIX)
app.include_router(reports.router,      prefix=PREFIX)
app.include_router(referrals.router,    prefix=PREFIX)
app.include_router(audit.router,        prefix=PREFIX)
app.include_router(setup.router,        prefix=PREFIX)
