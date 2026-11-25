from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.db.models import Base


def build_engine(database_url: str | None = None) -> AsyncEngine:
    """Create an async SQLAlchemy engine for PostgreSQL (asyncpg) or SQLite (aiosqlite)."""
    url = database_url or get_settings().DATABASE_URL
    is_sqlite = url.startswith("sqlite")
    kwargs: dict = {"echo": False, "future": True}
    if is_sqlite:
        kwargs["connect_args"] = {"check_same_thread": False}
    else:
        kwargs["pool_pre_ping"] = True
    return create_async_engine(url, **kwargs)


engine: AsyncEngine = build_engine()

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def init_db(target_engine: AsyncEngine | None = None) -> None:
    """Create database tables if they do not exist."""
    db_engine = target_engine or engine
    async with db_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db(target_engine: AsyncEngine | None = None) -> None:
    """Dispose database engine connection pools."""
    db_engine = target_engine or engine
    await db_engine.dispose()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session per request."""
    async with AsyncSessionLocal() as session:
        yield session
