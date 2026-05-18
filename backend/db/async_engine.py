from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    async_sessionmaker,
    create_async_engine
)

from config.settings import SQLAlchemySettings
import logging

logger = logging.getLogger(__name__)
    
def get_session_factory(engine: AsyncEngine):
    """Get the session factory for the SQLAlchemy engine."""
    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,  # Keep objects usable after commit
    )
    
    return session_factory

def get_async_engine(sqlalchemy_settings: SQLAlchemySettings) -> AsyncEngine:
    """Build the async engine"""

    engine = create_async_engine(
        sqlalchemy_settings.sqlalchemy_url,
        # Connection pool settings optimized for Cloud SQL
        pool_size=sqlalchemy_settings.MIN_CONNECTIONS,
        max_overflow=sqlalchemy_settings.MAX_CONNECTIONS- sqlalchemy_settings.MIN_CONNECTIONS,
        pool_pre_ping=True,  # Validate connections before use
        pool_recycle=1800,   # Recycle connections every 30 minutes (Cloud SQL friendly)
        pool_timeout=60,     # Wait up to 60 seconds for a connection
        # echo=settings.debug, # Log SQL queries in debug mode
    )
    return engine

    
async def close_async_engine(_async_engine: AsyncEngine):
    """Close global async engine."""

    if _async_engine:
        await _async_engine.dispose()
        logger.info("🛑 SQLAlchemy engine disposed")
        
async def check_connection(session: AsyncSession) -> bool:
    """Check if the database connection is established.
    
    Args:
        session: An async session.
    """
    from sqlalchemy import text
    result = await session.execute(text("SELECT 1"))
    return result.scalar() == 1
    