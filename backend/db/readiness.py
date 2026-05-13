import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from db.schema.extensions import REQUIRED_EXTENSIONS

logger = logging.getLogger(__name__)

from db.async_engine import check_connection


@dataclass(frozen=True, slots=True)
class CheckResult:
    """Result of a single readiness check."""
    name: str
    ok: bool
    message: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ReadinessReport:
    """Report on the readiness of the database."""
    checks: list[CheckResult] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(check.ok for check in self.checks)

    def get(self, name: str) -> CheckResult | None:
        return next((check for check in self.checks if check.name == name), None)


def log_readiness_report(report: ReadinessReport) -> None:
    """Emit one log line per failed check; summarize when all checks pass.
    
    Args:
        report: A report on the readiness of the database.
    """
    
    for check in report.checks:
        if check.ok:
            logger.debug(
                "Readiness check passed: %s",
                check.name,
                extra={"details": check.details},
            )
            continue

        logger.warning(
            "Readiness check failed: %s — %s",
            check.name,
            check.message,
            extra={"details": check.details},
        )

    if report.ok:
        logger.info("Database readiness checks passed.")

async def _check_table(
    session: AsyncSession,
    *,
    schema: str,
    table: str,
) -> CheckResult:
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
        return CheckResult(
            name="table",
            ok=exists,
            message=f"Table {fqtn} exists." if exists else f"Table {fqtn} not found.",
            details={"schema": schema, "table": table},
        )
    except Exception as exc:
        logger.exception("Table check failed for %s", fqtn)
        return CheckResult(
            name="table",
            ok=False,
            message=f"Table check failed for {fqtn}.",
            details={"schema": schema, "table": table, "error": repr(exc)},
        )


async def _check_table_has_rows(
    session: AsyncSession,
    *,
    schema: str,
    table: str,
    min_rows: int,
) -> CheckResult:
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
        return CheckResult(
            name="rows",
            ok=ok,
            message=(
                f"Table {fqtn} has {row_count} rows (need at least {min_rows})."
            ),
            details={"row_count": row_count, "min_rows": min_rows},
        )
    except Exception as exc:
        logger.exception("Row count check failed for %s", fqtn)
        return CheckResult(
            name="rows",
            ok=False,
            message=f"Row count check failed for {fqtn}.",
            details={"min_rows": min_rows, "error": repr(exc)},
        )


async def _check_table_extensions(session: AsyncSession) -> CheckResult:
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
        return CheckResult(
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
        return CheckResult(
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
    min_rows: int
) -> ReadinessReport:
    """Run database readiness checks and return a structured report.
    
    Args:
        session_factory: A factory for creating async sessions.
        schema: The schema to check.
        table: The table to check.
        min_rows: The minimum number of rows the table should have.
    """
    checks: list[CheckResult] = []

    async with session_factory() as session:
        # simple test connection (must be first and pass)
        if not await check_connection(session):
            raise ValueError("Database connection failed")

        # check if table exists and schema is correct
        table_check = await _check_table(session, schema=schema, table=table)
        checks.append(table_check)

        # check if table has rows
        rows = await _check_table_has_rows(
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
    from db.async_engine import close_async_engine, get_async_engine, get_session_factory
    from config.bootstrap import DatabaseConstants, IngestionConstants
    from db.schema import BookModel
    try:
        engine = get_async_engine()
        schema = DatabaseConstants.SCHEMA
        table = BookModel.__tablename__
        min_rows = IngestionConstants.APPROXIMATE_LOAD_LIMIT
        
        session_factory = get_session_factory(engine)
        report = await is_ready(session_factory, schema=schema, table=table, min_rows=min_rows)
        log_readiness_report(report)
    finally:
        if engine:
            await close_async_engine(engine)

    


if __name__ == "__main__":
    asyncio.run(main())
