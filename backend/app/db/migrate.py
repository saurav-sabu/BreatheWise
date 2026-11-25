import asyncio
import logging

from app.core.logging import configure_logging
from app.db.session import close_db, init_db

logger = logging.getLogger("breathewise.migrate")


async def run_migrations() -> None:
    """Idempotently initialize/upgrade all SQLAlchemy tables and indexes."""
    configure_logging()
    logger.info("Applying BreatheWise database schema...")
    await init_db()
    await close_db()
    logger.info("Database schema initialization complete.")


if __name__ == "__main__":
    asyncio.run(run_migrations())
