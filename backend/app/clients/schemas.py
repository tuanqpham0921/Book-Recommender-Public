import logging

from typing import List, Optional, Any

from .base import BaseLLMRequest

from app.config import settings
from app.common.utils import save_file
from app.common.messages import APIMessage, SystemMessage

logger = logging.getLogger(__name__)


class OpenAIRequest(BaseLLMRequest):
    model: str = settings.openai.BASE_MODEL
    system: SystemMessage
    messages: List[APIMessage]
    tools: list[dict] | None = None
    tool_choice: dict | str = None
    max_output_tokens: Optional[int] = None

    def to_payload(self) -> dict[str, Any]:
        messages = []
        if self.system:
            messages.append(self.system.model_dump())
        messages.extend([m.to_openai_dict() for m in self.messages])

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "seed": 42, 
        }
        if self.max_output_tokens:
            payload["max_output_tokens"] = self.max_output_tokens
        if self.tools:
            payload["tools"] = self.tools
            payload["tool_choice"] = self.tool_choice if self.tool_choice else "auto"

        return payload

    def export(self, file_name: str = "dev"):
        """Export the full request payload for logging/debugging."""
        payload = self.to_payload()
        save_file(payload, file_name=f"{file_name}_openai_request")
        logger.debug(f"📋 Exported OpenAI request payload: {payload}")
