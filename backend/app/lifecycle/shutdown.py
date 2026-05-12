import logging
import asyncio
from fastapi import FastAPI

from db import close_async_engine

logger = logging.getLogger(__name__)


async def shutdown_sqlalchemy_engine(app: FastAPI):
    engine = getattr(app.state, "sqlalchemy_engine", None)
    if engine:
        try:
            await close_async_engine(engine)
            logger.info("🧹 SQLAlchemy engine disposed")
        except Exception as e:
            logger.warning(f"⚠️ Failed to close SQLAlchemy: {e.__class__.__name__}")


async def shutdown_openai(app: FastAPI):
    client = getattr(app.state, "openai_client", None)
    if client and hasattr(client, "close"):
        try:
            await client.close()
            logger.info("🧹 OpenAI client closed")
        except Exception as e:
            logger.warning(f"⚠️ Failed to close OpenAI client: {e.__class__.__name__}")


async def shutdown_all(app: FastAPI):
    logger.info("🔻 Shutting down services...")
    await asyncio.gather(
        shutdown_openai(app),
        shutdown_sqlalchemy_engine(app),
    )
    logger.info("✅ All shutdown tasks completed")
