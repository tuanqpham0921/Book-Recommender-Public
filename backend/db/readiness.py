import asyncio
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from common import OperationReport, OperationResult
from db.async_engine import check_connection
from db.schema.extensions import REQUIRED_EXTENSIONS

logger = logging.getLogger(__name__)

CheckResult = OperationResult


class ReadinessReport(OperationReport):
    """Database readiness report with domain-specific logging."""

    def log(self, logger: logging.Logger | None = None) -> None:
        super().log(
            logger or logging.getLogger(__name__),
            success_summary="Database readiness checks passed.",
            check_label="Readiness check",
        )


async def _check_table(
    session: AsyncSession,
    *,
    schema: str,
    table: str,
) -> OperationResult:
    """Check if the table exists and the schema is correct.

    Args:
        session: An async session.
        schema: The schema to check.
        table: The table to check.
    """

    fqtn = f"{schema}.{table}"
    try:
        result = await session.execute(
            text("SELECT to_regclass(:fqtn) IS NOT NULL"),
            {"fqtn": fqtn},
        )
        exists = bool(result.scalar())
        return OperationResult(
            name="table",
            ok=exists,
            message=f"Table {fqtn} exists." if exists else f"Table {fqtn} not found.",
            details={"schema": schema, "table": table},
        )
    except Exception as exc:
        logger.exception("Table check failed for %s", fqtn)
        return OperationResult(
            name="table",
            ok=False,
            message=f"Table check failed for {fqtn}.",
            details={"schema": schema, "table": table, "error": repr(exc)},
        )


async def has_minimum_books(
    session: AsyncSession,
    *,
    schema: str,
    table: str,
    min_rows: int,
) -> OperationResult:
    """Check if the table has at least the minimum number of rows.

    Args:
        session: An async session.
        schema: The schema to check.
        table: The table to check.
        min_rows: The minimum number of rows the table should have.
    """
    fqtn = f"{schema}.{table}"
    try:
        result = await session.execute(text(f"SELECT COUNT(*) FROM {schema}.{table}"))
        row_count = int(result.scalar() or 0)
        ok = row_count >= min_rows
        return OperationResult(
            name="rows",
            ok=ok,
            message=(f"Table {fqtn} has {row_count} rows (need at least {min_rows})."),
            details={"row_count": row_count, "min_rows": min_rows},
        )
    except Exception as exc:
        logger.exception("Row count check failed for %s", fqtn)
        return OperationResult(
            name="rows",
            ok=False,
            message=f"Row count check failed for {fqtn}.",
            details={"min_rows": min_rows, "error": repr(exc)},
        )


async def _check_table_extensions(session: AsyncSession) -> OperationResult:
    """Check if the required PostgreSQL extensions are installed.

    Args:
        session: An async session.
    """
    required_extensions = list(REQUIRED_EXTENSIONS)
    try:
        result = await session.execute(
            text("SELECT extname FROM pg_extension WHERE extname = ANY(:extensions)"),
            {"extensions": required_extensions},
        )
        found = {row[0] for row in result.fetchall()}
        missing = [ext for ext in required_extensions if ext not in found]
        ok = not missing
        return OperationResult(
            name="extensions",
            ok=ok,
            message=(
                "Required PostgreSQL extensions are installed."
                if ok
                else f"Missing PostgreSQL extensions: {', '.join(missing)}."
            ),
            details={
                "required": required_extensions,
                "installed": sorted(found),
                "missing": missing,
            },
        )
    except Exception as exc:
        logger.exception("Extension check failed")
        return OperationResult(
            name="extensions",
            ok=False,
            message="Extension check failed.",
            details={"required": required_extensions, "error": repr(exc)},
        )


async def is_ready(
    session_factory: async_sessionmaker[AsyncSession],
    schema: str,
    table: str,
    *,
    min_rows: int,
) -> ReadinessReport:
    """Run database readiness checks and return a structured report.

    Args:
        session_factory: A factory for creating async sessions.
        schema: The schema to check.
        table: The table to check.
        min_rows: The minimum number of rows the table should have.
    """
    checks: list[OperationResult] = []

    async with session_factory() as session:
        # simple test connection (must be first and pass)
        if not await check_connection(session):
            raise ValueError("Database connection failed")

        # check if table exists and schema is correct
        table_check = await _check_table(session, schema=schema, table=table)
        checks.append(table_check)

        # check if table has rows
        rows = await has_minimum_books(
            session,
            schema=schema,
            table=table,
            min_rows=min_rows,
        )
        checks.append(rows)

        # check if required extensions are installed
        checks.append(await _check_table_extensions(session))

    return ReadinessReport(checks=checks)


# -----------------------------------------------------------------------------
# For testing purposes
# poetry run python db/readiness.py
# -----------------------------------------------------------------------------
async def main() -> None:
    from config import DatabaseConstants, IngestionConstants
    from db.async_engine import (
        close_async_engine,
        get_async_engine,
        get_session_factory,
    )
    from db.schema import BookModel
    from config.settings import sqlalchemy_settings

    engine = None
    try:
        engine = get_async_engine(sqlalchemy_settings)
        schema = DatabaseConstants.SCHEMA
        table = BookModel.__tablename__
        min_rows = IngestionConstants.APPROXIMATE_LOAD_LIMIT

        session_factory = get_session_factory(engine)
        report = await is_ready(
            session_factory, schema=schema, table=table, min_rows=min_rows
        )
        report.log()
    finally:
        if engine:
            await close_async_engine(engine)


if __name__ == "__main__":
    asyncio.run(main())
