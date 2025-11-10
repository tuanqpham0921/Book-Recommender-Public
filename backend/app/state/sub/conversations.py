import json
import logging
from typing import List, Dict

from app.common.types.session import SuffixEnum
from app.stores import SessionStore

logger = logging.getLogger(__name__)


class ConversationState:
    """Manages conversation history (Redis LIST)."""

    def __init__(self, session_store: SessionStore):
        self.store = session_store
        self.suffix = SuffixEnum.CONVERSATION

    async def add_messages(self, session_id: str, messages: List[Dict]):
        """Add messages to the conversation history."""
        return await self.store.list_rpush(session_id, self.suffix, *messages)

    async def get(self, session_id: str, left: int = 0, right: int = -1) -> List[Dict]:
        """Retrieve conversation messages"""
        all_messages = await self.store.list_range(session_id, self.suffix, left, right)
        if not all_messages:
            return []

        # Convert to list of dicts for easier processing
        return [json.loads(m) for m in all_messages]

    async def clear(self, session_id: str):
        """Clear conversation history."""
        await self.store.delete(session_id, self.suffix)
