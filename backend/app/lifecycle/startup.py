import asyncio
import logging
from fastapi import FastAPI
from typing import Any

from app.db import redis, postgres, sqlalchemy
from app.config.constants import AppConfig
from app.common.types.session import SuffixEnum, StorageType
from app.stores import SessionStore
from app.orchestration.orchestrator import Orchestrator
from app.config.settings import settings
from app.clients import OpenAIClient

logger = logging.getLogger(__name__)


async def _startup_task(name: str, coro, timeout: int):
    """
    Execute an async startup task with timeout and error handling.

    Args:
        name: Service name for logging
        coro: Async coroutine to execute
        timeout: Maximum seconds to wait

    Returns:
        Result from coroutine or None on failure
    """
    logger.info(f"Initializing {name}...")
    try:
        result = await asyncio.wait_for(coro(), timeout=timeout)
        logger.info(f"{name} initialized successfully")
        return result
    except asyncio.TimeoutError:
        logger.error(f"{name} init timeout after {timeout}s")
    except Exception as e:
        logger.error(f"{name} init failed: {e.__class__.__name__}: {e}")
    return None


async def start_openai_client() -> OpenAIClient:
    """Initialize OpenAI client with API key from settings."""
    if not settings.openai.API_KEY:
        raise ValueError("OpenAI API key not set")
    return OpenAIClient(api_key=settings.openai.API_KEY)


def start_orchestrator() -> Orchestrator:
    """Create task orchestration engine."""
    return Orchestrator()


async def start_redis():
    """
    Initialize Redis connection and session store.

    Returns:
        Tuple of (redis_client, session_store)
    """
    redis_client = await redis.init_redis()
    await redis_client.ping()
    store = SessionStore(
        redis_client, prefix=AppConfig.SESSION_PREFIX, env=settings.app.ENVIRONMENT
    )
    store.register_many(
        {
            SuffixEnum.METADATA: StorageType.JSON,
            SuffixEnum.CONVERSATION: StorageType.LIST,
            SuffixEnum.PREFS: StorageType.JSON,
        }
    )
    return redis_client, store


async def start_postgres():
    """Initialize Postgres connection pool."""
    return await postgres.init_postgres()


async def start_sqlalchemy_engine():
    """Initialize SQLAlchemy async engine and session factory."""
    return await sqlalchemy.init_sqlalchemy()


async def start_all(app: FastAPI):
    """
    Start all application services and attach to app state.

    Args:
        app: FastAPI application instance

    Raises:
        RuntimeError: If critical services fail to start
    """
    logger.info("Starting up all services...")

    try:
        app.state.openai_client = await _startup_task(
            "OpenAI client", start_openai_client, AppConfig.DEFAULT_TIMEOUT
        )
        if not app.state.openai_client:
            raise RuntimeError("OpenAI client startup failed")
    except Exception as e:
        logger.critical(f"Failed to start OpenAI client: {e}")
        raise

    app.state.pg_pool = await _startup_task(
        "Postgres", start_postgres, AppConfig.POSTGRES_TIMEOUT
    )
    if not app.state.pg_pool:
        logger.warning("Postgres service not available")

    sqlalchemy_result = await _startup_task(
        "SQLAlchemy", start_sqlalchemy_engine, AppConfig.POSTGRES_TIMEOUT
    )
    if sqlalchemy_result:
        app.state.sqlalchemy_engine, app.state.sqlalchemy_session_factory = (
            sqlalchemy_result
        )
    else:
        app.state.sqlalchemy_engine = None
        app.state.sqlalchemy_session_factory = None

    app.state.orchestrator = start_orchestrator()

    logger.info("Startup routine completed successfully.")
