import asyncio
import logging
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from db.schema.extensions import REQUIRED_EXTENSIONS

logger = logging.getLogger(__name__)

SCHEMA_DIR = Path(__file__).resolve().parent / "schema"


def _sql_statements(sql: str) -> list[str]:
    """Split the SQL file into individual statements."""
    statements: list[str] = []
    for chunk in sql.split(";"):
        lines = [
            line for line in chunk.splitlines()
            if line.strip() and not line.strip().startswith("--")
        ]
        if not lines:
            continue
        statements.append("\n".join(lines))
    return statements


async def _execute_sql_file(session: AsyncSession, path: Path) -> None:
    """Execute the SQL file."""
    for statement in _sql_statements(path.read_text(encoding="utf-8")):
        await session.execute(text(statement))


async def enable_extensions(session_factory: async_sessionmaker[AsyncSession]) -> None:
    """Install required PostgreSQL extensions."""
    async with session_factory() as session:
        await _execute_sql_file(session, SCHEMA_DIR / "00_extensions.sql")
        await session.commit()
    logger.info("Installed PostgreSQL extensions: %s", ", ".join(REQUIRED_EXTENSIONS))


async def init_tables(session_factory: async_sessionmaker[AsyncSession]) -> None:
    """Create application tables from schema SQL."""
    async with session_factory() as session:
        await _execute_sql_file(session, SCHEMA_DIR / "01_tables.sql")
        await session.commit()
    logger.info("Ensured books table exists.")


async def create_indexes(session_factory: async_sessionmaker[AsyncSession]) -> None:
    """Create database indexes from schema SQL."""
    async with session_factory() as session:
        await _execute_sql_file(session, SCHEMA_DIR / "02_indexes.sql")
        await session.commit()
    logger.info("Ensured books indexes exist.")


async def bootstrap_schema(session_factory: async_sessionmaker[AsyncSession]) -> None:
    """Apply extensions, tables, and indexes in order."""
    await enable_extensions(session_factory)
    await init_tables(session_factory)
    await create_indexes(session_factory)

# -----------------------------------------------------------------------------
# For testing purposes
# poetry run python db/bootstrap.py
# -----------------------------------------------------------------------------
async def main() -> None:
    from config.bootstrap import setup_logging
    from db.async_engine import close_async_engine, get_async_engine, get_session_factory

    setup_logging()
    engine = get_async_engine()
    try:
        session_factory = get_session_factory(engine)
        await bootstrap_schema(session_factory)
    finally:
        await close_async_engine(engine)


if __name__ == "__main__":
    asyncio.run(main())
