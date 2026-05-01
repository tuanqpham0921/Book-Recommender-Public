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


# --- Generic helper for async startup with timeout ---
async def _startup_task(name: str, coro, timeout: int):
    """Run an async startup task with logging and timeout."""
    logger.info(f"🔄 Initializing {name}...")
    try:
        result = await asyncio.wait_for(coro(), timeout=timeout)
        logger.info(f"✅ {name} initialized successfully")
        return result
    except asyncio.TimeoutError:
        logger.error(f"❌ {name} init timeout after {timeout}s")
    except Exception as e:
        logger.error(f"❌ {name} init failed: {e.__class__.__name__}: {e}")
    return None


# --- Individual service initializers ---
async def start_openai_client() -> OpenAIClient:
    if not settings.openai.API_KEY:
        raise ValueError("OpenAI API key not set")
    return OpenAIClient(api_key=settings.openai.API_KEY)


def start_orchestrator() -> Orchestrator:
    return Orchestrator()


async def start_redis():
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
    return await postgres.init_postgres()


async def start_sqlalchemy_engine():
    return await sqlalchemy.init_sqlalchemy()


# --- Main startup routine ---
async def start_all(app: FastAPI):
    logger.info("🔄 Starting up all services...")

    # Critical service: OpenAI client
    try:
        app.state.openai_client = await _startup_task(
            "OpenAI client", start_openai_client, AppConfig.DEFAULT_TIMEOUT
        )
        if not app.state.openai_client:
            raise RuntimeError("OpenAI client startup failed")
    except Exception as e:
        logger.critical(f"❌ Failed to start OpenAI client: {e}")
        raise

    # # Optional services
    # redis_result = await _startup_task("Redis", start_redis, AppConfig.REDIS_TIMEOUT)
    # if redis_result:
    #     app.state.redis, app.state.session_store = redis_result
    # else:
    #     logger.warning("⚠️ Redis service not available")

    app.state.pg_pool = await _startup_task(
        "Postgres", start_postgres, AppConfig.POSTGRES_TIMEOUT
    )
    if not app.state.pg_pool:
        logger.warning("⚠️ Postgres service not available")

    # SQLAlchemy returns tuple (engine, session_factory)
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

    logger.info("✅ Startup routine completed successfully.")
