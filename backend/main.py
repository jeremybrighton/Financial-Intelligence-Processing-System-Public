"""
Financial Intelligence Processing System — FastAPI Entry Point
FRC-side platform: intake, case management, legal KB, reports, referrals.

Start (local dev): uvicorn backend.main:app --reload --port 8000
Deployment: Vercel serverless via mangum ASGI adapter
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum

from backend.core.config import settings
from backend.core.database import create_indexes, ping_db
from backend.core.exceptions import register_exception_handlers
from backend.routers import audit, auth, cases, institutions, intake, legal, policy, referrals, reports, users

logging.basicConfig(level=logging.DEBUG if settings.DEBUG else logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger(__name__)

app = FastAPI(
    title=settings.APP_NAME, version=settings.APP_VERSION,
    description="FRC-side platform for financial intelligence intake, case management, legal reference, report generation, and referral routing.",
    docs_url="/docs", redoc_url="/redoc", openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET","POST","PUT","PATCH","DELETE","OPTIONS"],
    allow_headers=["Content-Type","Authorization","X-Institution-API-Key"],
)

register_exception_handlers(app)

@app.on_event("startup")
async def on_startup():
    log.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION} [{settings.ENVIRONMENT}]")
    if await ping_db():
        await create_indexes()
        log.info("Database ready.")
    else:
        log.error("Database connection failed on startup!")

@app.on_event("shutdown")
async def on_shutdown():
    from backend.core.database import get_client
    try: get_client().close()
    except: pass

@app.get("/", tags=["Health"])
async def root():
    return {"success":True,"service":settings.APP_NAME,"version":settings.APP_VERSION,"environment":settings.ENVIRONMENT,"status":"running"}

@app.get("/health", tags=["Health"])
async def health():
    db_ok=await ping_db()
    return {"success":True,"service":settings.APP_NAME,"version":settings.APP_VERSION,"environment":settings.ENVIRONMENT,"database":"connected" if db_ok else "unreachable"}

API_PREFIX = "/api/v1"
app.include_router(auth.router,         prefix=API_PREFIX)
app.include_router(users.router,        prefix=API_PREFIX)
app.include_router(institutions.router, prefix=API_PREFIX)
app.include_router(intake.router,       prefix=API_PREFIX)
app.include_router(cases.router,        prefix=API_PREFIX)
app.include_router(legal.router,        prefix=API_PREFIX)
app.include_router(reports.router,      prefix=API_PREFIX)
app.include_router(referrals.router,    prefix=API_PREFIX)
app.include_router(audit.router,        prefix=API_PREFIX)
app.include_router(policy.router,       prefix=API_PREFIX)

handler = Mangum(app, lifespan="off")
