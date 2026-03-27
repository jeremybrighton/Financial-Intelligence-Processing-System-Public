"""Health check router."""
from datetime import datetime, timezone
from fastapi import APIRouter
from app.core.database import ping_db

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check():
    db_ok = await ping_db()
    return {
        "status": "ok",
        "service": "FRC Backend",
        "database": "connected" if db_ok else "unreachable",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/")
async def root():
    return {
        "service": "Financial Intelligence Processing System",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
    }
