import asyncio
import logging
from fastapi import FastAPI
from typing import Any

from app.db import sqlalchemy
from config.constants import AppConfig
from app.orchestration.orchestrator import Orchestrator
from config.settings import settings
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
