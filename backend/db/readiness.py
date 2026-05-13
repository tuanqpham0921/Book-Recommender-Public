from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from config.bootstrap import DatabaseConstants, IngestionConstants
from db.schema import BookModel

async def check_table(
    session_factory: async_sessionmaker[AsyncSession],
    schema: str = DatabaseConstants.SCHEMA,
    table: str = BookModel.__tablename__,
):
    """Check if the table exists"""

    async with session_factory() as session:
        q_exists = text(
            """
            select to_regclass(:fqtn) is not null as exists_;"""
        )

        fqtn = f"{schema}.{table}"
        result = await session.execute(q_exists, {"fqtn": fqtn})
        table_exists = bool(result.scalar())

        if not table_exists:
            print(f"❌ Table {schema}.{table} not found")
            return False

        print(f"✅ Table {schema}.{table} found")
        return True


async def check_table_has_rows(
    session_factory: async_sessionmaker[AsyncSession],
    schema: str = DatabaseConstants.SCHEMA,
    table: str = BookModel.__tablename__,
):
    """Check if the table has more than LOAD_LIMIT rows"""

    async with session_factory() as session:
        q_count = text(f"SELECT COUNT(*) FROM {schema}.{table}")
        result = await session.execute(q_count)
        row_count = int(result.scalar() or 0)

        print(f"Table {schema}.{table} has {row_count} rows")
        return row_count > IngestionConstants.APPROXIMATE_LOAD_LIMIT


async def check_table_extensions(
    session_factory: async_sessionmaker[AsyncSession],
    schema: str = DatabaseConstants.SCHEMA,
    table: str = BookModel.__tablename__,
):
    """Check if the table has the correct extensions"""

    async with session_factory() as session:
        q_extensions = text(
            f"SELECT extname FROM pg_extension WHERE extname = 'pgvector' AND extnamespace = '{schema}'"
        )
        result = await session.execute(q_extensions)
        extensions = result.fetchall()

        if len(extensions) == 0:
            print(f"❌ Extensions for {schema}.{table} not found")
            return False

        print(f"✅ Extensions for {schema}.{table} found")
        return True


async def is_ready(
    session_factory: async_sessionmaker[AsyncSession],
    schema: str = DatabaseConstants.SCHEMA,
    table: str = BookModel.__tablename__,
):
    """Check if the table is ready"""
    return (
        await check_table(session_factory, schema, table)
        and await check_table_has_rows(session_factory, schema, table)
        and await check_table_extensions(session_factory, schema, table)
    )