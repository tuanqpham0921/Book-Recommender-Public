import logging
import asyncpg

from pgvector.asyncpg import register_vector

from app.config import settings

logger = logging.getLogger(__name__)


async def init_postgres():
    """Initialize global Postgres pool with pgvector support."""
    try:

        async def init_conn(conn):
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
            await register_vector(conn)

        pool = await asyncpg.create_pool(
            host=settings.postgres.HOST,
            port=settings.postgres.PORT,
            database=settings.postgres.DB,
            user=settings.postgres.USER,
            password=settings.postgres.PASSWORD,
            min_size=settings.postgres.MIN_CONNECTIONS,
            max_size=settings.postgres.MAX_CONNECTIONS,
            init=init_conn,  # runs for every new connection in the pool
        )
        return pool

    except Exception as e:
        logger.error(f"Failed to connect to PostgreSQL: {e}")
        return None


async def close_postgres(pool):
    """Close global Postgres pool."""
    if pool:
        await pool.close()
        logger.info("🛑 Postgres closed")


async def clear_postgres_db(pool):
    """Clear all data from PostgreSQL database."""
    if pool is None:
        raise RuntimeError("Postgres pool is not initialized")

    async with pool.acquire() as conn:  # ✅ borrow from pool
        try:
            await conn.execute("DROP TABLE IF EXISTS books;")
            logger.info("PostgreSQL database cleared successfully")
        except Exception as e:
            logger.error(f"Error clearing PostgreSQL database: {e}")
            raise



