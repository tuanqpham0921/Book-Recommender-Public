import logging

from uuid import uuid4
from fastapi import APIRouter, Request, HTTPException, Depends

from app.api.dependencies import get_redis, get_state_manager
from app.api.schemas import SessionOut
from app.common.utils import now_iso

logger = logging.getLogger(__name__)
# Store assistant instances to access book results
router = APIRouter(tags=["Session"])


@router.post("/session/new", response_model=SessionOut)
async def create_new_session(request: Request):
    """Create a new session, initialize metadata."""
    try:
        session_id = str(uuid4())[:8]
        logger.info(f"🆕 Created new session {session_id}")
        return SessionOut(id=session_id, created_at=now_iso())

    except Exception:
        logger.exception("❌ Failed to create session")
        raise HTTPException(status_code=500, detail="Failed to create session")


@router.get("/cache/stats")
async def get_cache_stats(redis=Depends(get_redis)):
    """Example Redis operations."""
    try:
        info = await redis.info("memory")
        return {
            "used_memory": info.get("used_memory_human", "unknown"),
            "connected_clients": await redis.client_list(),
            "total_keys": await redis.dbsize(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cache stats failed: {str(e)}")


@router.get("/session/{session_id}/recommended_books")
async def get_session_recommended_books(
    session_id: str, state_manager=Depends(get_state_manager)
):
    """Get recommended books for a session."""
    try:
        recommendations = await state_manager.load_recommendations(session_id)
        return {
            "books": recommendations,
            "session_id": session_id,
            "count": len(recommendations),
        }
    except Exception as e:
        logger.exception(f"❌ Failed to get recommendations for session {session_id}")
        raise HTTPException(
            status_code=500, detail="Failed to retrieve recommendations"
        )
