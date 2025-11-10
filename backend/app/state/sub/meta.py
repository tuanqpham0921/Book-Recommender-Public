import json
import logging

from app.common.types.session import SuffixEnum
from app.stores import SessionStore

logger = logging.getLogger(__name__)


class MetaState:
    """Manages session metadata (Redis HASH)."""

    def __init__(self, session_store: SessionStore):
        self.store = session_store
        self.suffix = SuffixEnum.METADATA

    async def set(self, session_id: str, key: str, value: str):
        """Update session metadata (one or more fields)."""
        await self.store.set(session_id, self.suffix, {key: value})

    async def update_field(self, session_id: str, key: str, value: str):
        """Update a single metadata field."""
        await self.store.set(session_id, self.suffix, {key: value})

    async def get(self, session_id: str):
        """Retrieve session metadata."""
        data = await self.store.get(session_id, self.suffix)
        return data if data else None

    async def clear(self, session_id: str):
        """Delete session metadata."""
        await self.store.delete(session_id, self.suffix)
