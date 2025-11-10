import os
import json
import logging
from typing import List

from app.stores.session_store import SessionStore

from app.common.messages import APIMessage
from app.state.schemas import SessionState
from app.common.utils import redis_chat_deserialization, save_file

from app.state.sub.meta import MetaState
from app.state.sub.prefs import PreferencesState
from app.state.sub.conversations import ConversationState

logger = logging.getLogger(__name__)


class StateManager:
    """High-level state manager coordinating sub-state managers."""

    def __init__(self, store: SessionStore):
        self.store = store

        # Sub-states
        self.conversations = ConversationState(session_store=self.store)
        self.preferences = PreferencesState(session_store=self.store)
        self.metadata = MetaState(session_store=self.store)

    async def add_messages_to_redis(self, session_id: str, messages: List[APIMessage]):
        """Add multiple messages to the conversation history."""
        try:
            num_added = await self.conversations.add_messages(
                session_id, [m.model_dump_json() for m in messages]
            )
            logger.info(f"➕ Persisted {num_added} messages for session {session_id}")
        except Exception as e:
            logger.error(f"❌ Failed to persist messages for session {session_id}: {e}")

    async def get_chat_history(self, session_id: str) -> List[APIMessage]:
        """Retrieve all conversation messages."""
        # TODO: add pagination support (limit, offset)
        try:
            conversation_history = await self.conversations.get(session_id)
            return redis_chat_deserialization(conversation_history)
        except Exception as e:
            logger.error(
                f"❌ Failed to retrieve conversation history for session {session_id}: {e}"
            )
            return []

    async def get_snapshot(self, session_id: str) -> SessionState:
        """
        Assemble a full SessionState snapshot from sub-states.
        Handles failures gracefully and logs issues.
        """
        # Defaults
        meta = None
        prefs = None
        messages = []

        try:
            messages = await self.get_chat_history(session_id)
        except Exception as e:
            logger.warning(f"⚠️ Failed to load messages for session {session_id}: {e}")

        # Build snapshot, tolerate missing sub-states
        snapshot = SessionState(
            session_id=session_id,
            # session_meta=meta,
            user_preferences=prefs,
            conversation_history=messages,
        )

        logger.debug(f"📋 Snapshot built for session {session_id}")
        return snapshot

    async def export_snapshot(
        self, session_id: str, file_name: str = "dev", output_file: str = "logs/"
    ):
        """Export the full session snapshot to a JSON file."""
        snapshot = await self.get_snapshot(session_id)
        save_file(snapshot.model_dump(), file_name=f"{file_name}_snapshot")