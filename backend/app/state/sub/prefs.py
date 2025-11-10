import logging
from typing import Optional

from app.common.types.session import SuffixEnum
from app.stores import SessionStore
from app.state.schemas import Preferences


class PreferencesState:
    """Manages user preferences (Redis JSON)."""

    def __init__(self, session_store: SessionStore):
        self.store = session_store
        self.suffix = SuffixEnum.PREFS
        self.logger = logging.getLogger(self.__class__.__name__)

    async def set(self, session_id: str, prefs: Preferences):
        """Save user preferences."""
        try:
            await self.store.set(session_id, self.suffix, prefs.model_dump())
            self.logger.debug(f"💾 Saved preferences for session {session_id}")
        except Exception as e:
            self.logger.error(
                f"❌ Failed to save preferences for session {session_id}: {e}"
            )
            raise

    async def get(self, session_id: str) -> Optional[Preferences]:
        """Fetch user preferences."""
        try:
            raw = await self.store.get(session_id, self.suffix)
            if not raw:
                self.logger.debug(f"ℹ️ No preferences found for session {session_id}")
                return None
            return Preferences.model_validate(raw)
        except Exception as e:
            self.logger.warning(
                f"⚠️ Failed to load preferences for session {session_id}: {e}"
            )
            return None

    async def clear(self, session_id: str):
        """Delete user preferences."""
        try:
            await self.store.delete(session_id, self.suffix)
            self.logger.info(f"🗑️ Cleared preferences for session {session_id}")
        except Exception as e:
            self.logger.error(
                f"❌ Failed to clear preferences for session {session_id}: {e}"
            )
