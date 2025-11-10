import time
import logging
import asyncio

from sqlalchemy import text
from fastapi import APIRouter, Request
from app.config import AppConfig

from app.api.schemas import HealthStatus

logger = logging.getLogger(__name__)

router = APIRouter(tags=["System"])


@router.post("/health", include_in_schema=False)
def health_check():
    """Basic health check - always returns ok if app is running."""
    return {"status": "ok", "timestamp": time.time()}


# TODO: use the depend on get core services
@router.post("/ready", include_in_schema=False, response_model=HealthStatus)
async def detailed_health_check(request: Request):
    """Detailed health check with service status."""

    return {"status": "ready", "service": "book-recommender-api", "version": "3.0.0"}

    health = HealthStatus()

    # Check services if available
    if hasattr(request.app.state, "health_status"):
        startup_status = request.app.state.health_status
        health.postgres = startup_status.get("postgres", False)
        health.redis = startup_status.get("redis", False)
        health.openai = startup_status.get("openai", False)
        health.orchestrator = startup_status.get("orchestrator", False)
        health.sqlalchemy_engine = startup_status.get("sqlalchemy_engine", False)

    # Quick connectivity tests for active services
    if health.redis and hasattr(request.app.state, "redis") and request.app.state.redis:
        try:
            await request.app.state.redis.ping()
            health.redis = True
        except Exception:
            health.redis = False

    if (
        health.postgres
        and hasattr(request.app.state, "pg_pool")
        and request.app.state.pg_pool
    ):
        try:
            async with request.app.state.pg_pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            health.postgres = True
        except Exception:
            health.postgres = False

    if (
        health.sqlalchemy_engine
        and hasattr(request.app.state, "sqlalchemy_engine")
        and request.app.state.sqlalchemy_engine
    ):
        async with request.app.state.sqlalchemy_engine.begin() as conn:
            # Test connection
            result = await conn.execute(text("SELECT 1 as test"))
            test_value = result.scalar()
            if test_value == 1:
                logger.info("✅ SQLAlchemy connection test passed")

    if (
        health.openai
        and hasattr(request.app.state, "openai_client")
        and request.app.state.openai_client
    ):
        try:
            # Lightweight OpenAI API call to verify connectivity
            # Using models.list() as it's a simple, fast endpoint
            models = await asyncio.wait_for(
                request.app.state.openai_client.client.models.list(),
                timeout=AppConfig.OPENAI_TIMEOUT,
            )
            health.openai = True
        except asyncio.TimeoutError:
            health.openai = False
        except Exception:
            health.openai = False

    # Determine overall status
    all_healthy = all(
        [health.postgres, health.redis, health.openai, health.orchestrator]
    )
    core_healthy = health.redis and health.openai and health.orchestrator

    if all_healthy:
        health.message = "All services healthy"
    elif core_healthy:
        health.message = "Core services healthy, some optional services degraded"
    else:
        health.message = "Service degradation detected"

    return health
