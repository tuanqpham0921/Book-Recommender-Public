from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import text
from app.config.settings import settings
import logging

logger = logging.getLogger(__name__)


async def init_sqlalchemy():
    """Initialize global SQLAlchemy engine with pgvector support."""

    try:
        # Connection arguments for Cloud SQL
        connect_args = {
            "server_settings": {
                "application_name": "book-recommender-backend",
            }
        }

        # Add Cloud SQL specific settings if using socket connection
        if settings.postgres.HOST.startswith("/cloudsql/"):
            connect_args.update(
                {
                    # Note: connect_timeout is not supported by asyncpg through SQLAlchemy
                    "server_settings": {
                        "application_name": "book-recommender-backend",
                    },
                }
            )

        logger.info(
            f"🔗 Connecting to SQLAlchemy: {settings.postgres.sqlalchemy_url.replace(settings.postgres.PASSWORD, '***')}"
        )

        # Create async engine with connection pooling
        _sqlalchemy_engine = create_async_engine(
            settings.postgres.sqlalchemy_url,
            # Connection pool settings optimized for Cloud SQL
            pool_size=settings.postgres.MIN_CONNECTIONS,
            max_overflow=settings.postgres.MAX_CONNECTIONS
            - settings.postgres.MIN_CONNECTIONS,
            pool_pre_ping=True,  # Validate connections before use
            pool_recycle=1800,  # Recycle connections every 30 minutes (Cloud SQL friendly)
            pool_timeout=60,  # Wait up to 60 seconds for a connection
            # echo=settings.debug, # Log SQL queries in debug mode
            connect_args=connect_args,
        )

        # TODO: Move this to a separate function
        # Test connection and setup pgvector
        async with _sqlalchemy_engine.begin() as conn:
            # Test connection
            await conn.execute(text("SELECT 1"))
            logger.info("✅ Database connection test successful")

            # Enable pgvector extension
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            logger.info("✅ pgvector extension enabled")

            # Import models to ensure they're registered
            from app.db.models import BookModel, Base

            # Create tables if they don't exist (for development)
            # In production, you should use Alembic migrations
            try:
                # Check if books table exists
                result = await conn.execute(
                    text(
                        """
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = 'books'
                    )
                """
                    )
                )
                table_exists = result.scalar()

                if table_exists:
                    logger.info("✅ Books table already exists")
                else:
                    logger.info(
                        "⚠️ Books table not found - this is expected if using direct asyncpg setup"
                    )

            except Exception as e:
                logger.warning(f"⚠️ Could not check table existence: {e}")

        logger.info("✅ SQLAlchemy engine initialized successfully")

        # Create session factory
        _sqlalchemy_session_factory = async_sessionmaker(
            _sqlalchemy_engine,
            class_=AsyncSession,
            expire_on_commit=False,  # Keep objects usable after commit
        )

        return _sqlalchemy_engine, _sqlalchemy_session_factory

    except Exception as e:
        logger.error(f"❌ SQLAlchemy initialization failed: {e}")
        logger.error(
            f"   Database URL: {settings.postgres.sqlalchemy_url.replace(settings.postgres.PASSWORD, '***')}"
        )
        return None, None


async def close_sqlalchemy(_sqlalchemy_engine):
    """Close global SQLAlchemy engine."""

    if _sqlalchemy_engine:
        await _sqlalchemy_engine.dispose()
        logger.info("🛑 SQLAlchemy engine disposed")
