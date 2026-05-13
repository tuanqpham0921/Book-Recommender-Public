from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from config import settings
from config.bootstrap import IngestionConstants


async def check_table_exists(
    session_factory: async_sessionmaker[AsyncSession],
    schema: str = settings.sqlalchemy.SCHEMA,
    table: str = settings.sqlalchemy.TABLE,
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
    
async def check_table_schema(
    session_factory: async_sessionmaker[AsyncSession],
    schema: str = settings.sqlalchemy.SCHEMA,
    table: str = settings.sqlalchemy.TABLE,
):
    """Check if the table has the correct schema"""

    async with session_factory() as session:
        q_schema = text(f"SELECT schema_name FROM information_schema.tables WHERE table_name = '{table}'")
        result = await session.execute(q_schema)
        schema_name = result.scalar()
        
        if schema_name != schema:
            print(f"❌ Table {schema}.{table} has schema {schema_name} instead of {schema}")
            return False
        print(f"✅ Table {schema}.{table} has schema {schema_name}")
        return True
    
async def check_table_has_enough_rows(
    session_factory: async_sessionmaker[AsyncSession],
    schema: str = settings.sqlalchemy.SCHEMA,
    table: str = settings.sqlalchemy.TABLE,
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
    schema: str = settings.sqlalchemy.SCHEMA,
    table: str = settings.sqlalchemy.TABLE,
):
    """Check if the table has the correct extensions"""

    async with session_factory() as session:
        q_extensions = text(f"SELECT extname FROM pg_extension WHERE extname = 'pgvector' AND extnamespace = '{schema}'")
        result = await session.execute(q_extensions)
        extensions = result.fetchall()
        
        if len(extensions) == 0:
            print(f"❌ Extensions for {schema}.{table} not found")
            return False
        
        print(f"✅ Extensions for {schema}.{table} found")
        return True
        
async def is_ready(
    session_factory: async_sessionmaker[AsyncSession],
    schema: str = settings.sqlalchemy.SCHEMA,
    table: str = settings.sqlalchemy.TABLE,
):
    """Check if the table is ready"""
    return (await check_table_exists(session_factory, schema, table) 
            and await check_table_has_enough_rows(session_factory, schema, table) 
            and await check_table_extensions(session_factory, schema, table)
            and await check_table_schema(session_factory, schema, table))
    
# ---------------------------------
# Database Enable/Create functions
# ---------------------------------
async def enable_extensions(
    session_factory: async_sessionmaker[AsyncSession],
    schema: str = settings.sqlalchemy.SCHEMA,
    table: str = settings.sqlalchemy.TABLE,
):
    """Enable the extensions for the table"""

    async with session_factory() as session:
        q_extensions = text(f"CREATE EXTENSION IF NOT EXISTS pgvector;")
        await session.execute(q_extensions)
        print(f"✅ Extensions for {schema}.{table} enabled")
        
async def create_index(
    session_factory: async_sessionmaker[AsyncSession],
    schema: str = settings.sqlalchemy.SCHEMA,
    table: str = settings.sqlalchemy.TABLE,
):
    """Create the index for the table"""

    async with session_factory() as session:
        q_index = text(f"CREATE INDEX IF NOT EXISTS idx_{table} ON {schema}.{table} USING pgvector;")
        await session.execute(q_index)
        print(f"✅ Index for {schema}.{table} created")
        
async def create_table(
    session_factory: async_sessionmaker[AsyncSession],
    schema: str = settings.sqlalchemy.SCHEMA,
    table: str = settings.sqlalchemy.TABLE,
):
    """Create the table"""

    async with session_factory() as session:
        q_table = text(f"CREATE TABLE IF NOT EXISTS {schema}.{table} (id SERIAL PRIMARY KEY);")
        await session.execute(q_table)
        print(f"✅ Table {schema}.{table} created")
        
async def create_schema(
    session_factory: async_sessionmaker[AsyncSession],
    schema: str = settings.sqlalchemy.SCHEMA,
):
    """Create the schema"""

    async with session_factory() as session:
        q_schema = text(f"CREATE SCHEMA IF NOT EXISTS {schema};")
        await session.execute(q_schema)
        print(f"✅ Schema {schema} created")