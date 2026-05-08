import logging

from uuid import uuid4
from fastapi import APIRouter, Request, HTTPException, Depends

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