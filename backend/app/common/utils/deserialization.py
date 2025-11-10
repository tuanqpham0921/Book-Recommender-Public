import logging

from typing import List, Dict

from app.common.enums import Role
from app.common.messages import (
    UserMessage,
    AssistantMessage,
    ToolMessage,
    SystemMessage,
    APIMessage,
)

logger = logging.getLogger(__name__)


def redis_chat_deserialization(messages: List[Dict]) -> List[APIMessage]:
    """Convert Redis-stored message dict back to APIMessage."""

    result = []
    for msg in messages:
        try:
            if msg["role"] == Role.USER.value:
                result.append(UserMessage.model_validate(msg))
            elif msg["role"] == Role.ASSISTANT.value:
                result.append(AssistantMessage.model_validate(msg))
            elif msg["role"] == Role.TOOL.value:
                result.append(ToolMessage.model_validate(msg))
            elif msg["role"] == Role.SYSTEM.value:
                result.append(SystemMessage.model_validate(msg))
        except Exception as e:
            logger.warning(f"⚠️ Failed to parse message: {e}; raw: {msg}")

    logger.debug(f"✅ Successfully parsed {len(result)} messages for chat")

    return result
