from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.advisor import router as advisor_router
from app.api.v1.aqi import router as aqi_router
from app.api.v1.chat import router as chat_router
from app.api.v1.community import router as community_router
from app.api.v1.health import router as health_router
from app.api.v1.impact import router as impact_router
from app.api.v1.profiles import router as profiles_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.security import SecurityHeadersMiddleware, SlidingWindowRateLimiterMiddleware
from app.db.session import close_db, init_db


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Initialize database schema on startup and dispose pools on shutdown."""
    await init_db()
    yield
    await close_db()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance."""
    configure_logging()
    settings = get_settings()

    application = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="BreatheWise — GenAI-powered Urban Air Quality Assistant API",
        lifespan=lifespan,
    )

    application.add_middleware(SecurityHeadersMiddleware)
    application.add_middleware(
        SlidingWindowRateLimiterMiddleware,
        max_requests_per_minute=settings.RATE_LIMIT_PER_MINUTE,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
    )

    application.include_router(health_router, prefix=settings.API_V1_PREFIX)
    application.include_router(aqi_router, prefix=settings.API_V1_PREFIX)
    application.include_router(profiles_router, prefix=settings.API_V1_PREFIX)
    application.include_router(advisor_router, prefix=settings.API_V1_PREFIX)
    application.include_router(chat_router, prefix=settings.API_V1_PREFIX)
    application.include_router(impact_router, prefix=settings.API_V1_PREFIX)
    application.include_router(community_router, prefix=settings.API_V1_PREFIX)
    return application


app = create_app()
