import time
import logging
import asyncio

from sqlalchemy import text
from fastapi import APIRouter, Request
from config import AppConfig

from app.api.schemas import HealthStatus

logger = logging.getLogger(__name__)

router = APIRouter(tags=["System"])


@router.get("/health", include_in_schema=False)
def health_check():
    """Basic health check - always returns ok if app is running."""
    return {"status": "ok", "timestamp": time.time()}


# TODO: use the depend on get core services
@router.get("/ready", include_in_schema=False, response_model=HealthStatus)
async def detailed_health_check(request: Request):
    """Detailed health check with service status."""
    ...