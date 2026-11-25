from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_db

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    app_name: str
    environment: str
    version: str
    timestamp: datetime
    database_status: str
    qdrant_mode: str
    gemini_configured: bool
    cpcb_configured: bool


@router.get("/health", response_model=HealthResponse)
async def health_check(db: AsyncSession = Depends(get_db)) -> HealthResponse:
    """Return service health, DB connectivity check, and configuration readiness (no secrets)."""
    settings = get_settings()
    db_status = "ok"
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"

    qdrant_mode = "in_memory" if settings.QDRANT_URL.strip() == ":memory:" else "remote_or_disk"

    return HealthResponse(
        status="ok" if db_status == "ok" else "degraded",
        app_name=settings.APP_NAME,
        environment=settings.APP_ENV,
        version=settings.APP_VERSION,
        timestamp=datetime.now(timezone.utc),
        database_status=db_status,
        qdrant_mode=qdrant_mode,
        gemini_configured=settings.gemini_configured,
        cpcb_configured=settings.cpcb_configured,
    )
