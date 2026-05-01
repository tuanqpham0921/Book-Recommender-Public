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


async def setup_postgres_db(pool):
    """Create database tables and enable pgvector extension."""
    if pool is None:
        raise RuntimeError("Postgres pool is not initialized")

    async with pool.acquire() as conn:
        try:
            async with conn.transaction():  # ✅ all-or-nothing
                await conn.execute("DROP TABLE IF EXISTS books;")
                await conn.execute(
                    f"""
                    CREATE TABLE books (
                        isbn13 TEXT PRIMARY KEY,
                        title TEXT NOT NULL,
                        authors TEXT,
                        categories TEXT,
                        genre TEXT,
                        description TEXT,
                        published_year INTEGER,
                        average_rating FLOAT,
                        num_pages INTEGER,
                        ratings_count INTEGER,
                        thumbnail TEXT,
                        large_thumbnail TEXT,
                        title_and_subtiles TEXT,
                        anger FLOAT DEFAULT 0.0,
                        disgust FLOAT DEFAULT 0.0,
                        fear FLOAT DEFAULT 0.0,
                        joy FLOAT DEFAULT 0.0,
                        sadness FLOAT DEFAULT 0.0,
                        surprise FLOAT DEFAULT 0.0,
                        neutral FLOAT DEFAULT 0.0,
                        is_children BOOLEAN DEFAULT FALSE,
                        embedding VECTOR({settings.openai.EMBEDDING_DIMENSIONS})
                    );
                """
                )
                await conn.execute(
                    """
                    CREATE INDEX books_embedding_idx 
                    ON books USING ivfflat (embedding vector_cosine_ops)
                    WITH (lists = 100);
                """
                )
            logger.info("✅ PostgreSQL database setup completed successfully!")
        except Exception as e:
            logger.error(f"❌ Error setting up database: {e}")
            raise
