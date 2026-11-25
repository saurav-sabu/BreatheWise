import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.session import build_engine, init_db, close_db


@pytest.fixture
async def db_session():
    """Provide an isolated in-memory SQLite async session per test."""
    test_engine = build_engine("sqlite+aiosqlite:///:memory:")
    await init_db(test_engine)
    session_factory = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    async with session_factory() as session:
        yield session
    await close_db(test_engine)
