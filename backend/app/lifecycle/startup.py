import asyncio
import logging
from fastapi import FastAPI
from typing import Any

from sqlalchemy.ext.asyncio import AsyncEngine
from db import get_async_engine, get_session_factory, close_async_engine
from config import AppConfig, settings
from app.orchestration.orchestrator import Orchestrator
from app.clients import OpenAIClient

# TODO: there are redundant startup tasks for the same service, we should refactor this
# and use a single startup task for all services.

logger = logging.getLogger(__name__)

async def _startup_task(name: str, coro, timeout: int):
    """Generic helper to run an async startup task with logging and timeout."""
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


async def start_openai_client() -> OpenAIClient:
    """Start the OpenAI client."""
    if not settings.openai.API_KEY:
        raise ValueError("OpenAI API key not set")
    return OpenAIClient(api_key=settings.openai.API_KEY)


def start_orchestrator() -> Orchestrator:
    """Start the orchestrator."""
    return Orchestrator()

async def start_sqlalchemy_engine():
    """Start the SQLAlchemy engine."""
    return get_async_engine()

# --- Main startup routine ---
async def start_all(app: FastAPI):
    logger.info("🔄 Starting up all services...")

    # Critical service: OpenAI client
    app.state.openai_client = await _startup_task(
        "OpenAI client", start_openai_client, AppConfig.DEFAULT_TIMEOUT
    )
    if not app.state.openai_client:
        raise RuntimeError("OpenAI client startup failed")

    # Engine first; session factory is derived from the same engine (single pool).
    # TODO: optional health check / migrations before accepting traffic.
    app.state.sqlalchemy_engine = await _startup_task(
        "SQLAlchemy", start_sqlalchemy_engine, AppConfig.DATABASE_TIMEOUT
    )
    if not app.state.sqlalchemy_engine:
        raise RuntimeError("SQLAlchemy startup failed")
    
    # Get the session factory from the engine
    app.state.sqlalchemy_session_factory = get_session_factory(app.state.sqlalchemy_engine)

    # Orchestrator service
    app.state.orchestrator = start_orchestrator()
    if not app.state.orchestrator:
        raise RuntimeError("Orchestrator startup failed")

    logger.info("✅ Startup routine completed successfully.")
