import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from app.common.enums import Role
from app.common.utils import now_iso, save_file
from app.common.messages import APIMessage, UserMessage, AssistantMessage, ToolMessage
from app.clients.openai_client import OpenAIClient
from app.stores.book_store import BookStore
from app.common.sse_stream import SSEStream

logger = logging.getLogger(__name__)


@dataclass
class RequestContext:
    """Enhanced request context with separated conversation streams."""

    # Core identifiers
    session_id: str = None
    user_message: UserMessage = None

    # Services
    llm_client: OpenAIClient = None
    book_store: BookStore = None
    sse_stream: SSEStream = None

    # Internal LLM calls
    pipeline_conversation: List[APIMessage] = field(default_factory=list)

    # Pipeline state
    pipeline_context: Dict[str, Any] = field(default_factory=dict)
    current_step: Optional[str] = None

    # Results from each step
    step_results: Dict[str, Any] = field(default_factory=dict)

    # TODO: we might need this instead of just querying
    context_size: int = 0
    # context_messages: List[APIMessage] = field(default_factory=list)

    # user facing messages
    chat_messages: List[APIMessage] = field(default_factory=list)
    timestamp: str = field(default_factory=now_iso)

    def __post_init__(self):
        if self.user_message:
            self.chat_messages.append(self.user_message)
            self.pipeline_conversation.append(self.user_message)

    def add_chat_message(self, message: APIMessage):
        """Add message to user-facing conversation."""
        self.chat_messages.append(message)
        logger.debug(f"Added user message: {type(message).__name__}")

    def add_pipeline_message(self, message: APIMessage):
        """Add message to internal pipeline conversation."""
        self.pipeline_conversation.append(message)
        logger.debug(f"Added pipeline message: {type(message).__name__}")

    def get_conversation_for_llm(
        self, include_pipeline: bool = True
    ) -> List[APIMessage]:
        """Get conversation for LLM calls."""
        if include_pipeline:
            return self.pipeline_conversation.copy()
        return self.chat_messages.copy()

    def set_step_result(self, step_name: str, result: Any):
        """Store result from a pipeline step."""
        self.step_results[step_name] = result
        logger.debug(f"Stored result for step '{step_name}': {type(result).__name__}")

    def get_step_result(self, step_name: str) -> Any:
        """Get result from a previous pipeline step."""
        return self.step_results.get(step_name)

    def set_current_step(self, step_name: str):
        """Set the current pipeline step."""
        self.current_step = step_name
        logger.debug(f"Current step: {step_name}")

    def get_pipeline_summary(self) -> Dict[str, Any]:
        """Get summary of pipeline execution."""
        return {
            "current_step": self.current_step,
            "completed_steps": list(self.step_results.keys()),
            "pipeline_messages_count": len(self.pipeline_conversation),
            "chat_messages_count": len(self.chat_messages),
        }
        
    def add_message(self, message: APIMessage, background: bool = True):
        """Add a message to the in-memory context and optionally persist it asynchronously."""
        if (hasattr(message, "tool_calls") and message.tool_calls) or (
            message.role == Role.TOOL
        ):
            self.add_pipeline_message(message)
        else:
            self.add_chat_message(message)

    # -----------------------------------------------------------------------------------
    def export_user_context(self, file_name: str = "dev"):
        user_message = self.user_message.model_dump()
        chat_messages = [m.model_dump() for m in self.chat_messages]

        context = {
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "user_message": user_message,
            "chat_messages": chat_messages,
        }
        save_file(context, file_name=f"{file_name}_request_context_reponse")

    def export_pipeline_context(self, file_name: str = "dev"):
        user_message = self.user_message.model_dump() if self.user_message else None
        pipeline_conversation = [m.model_dump() for m in self.pipeline_conversation]

        context = {
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "user_message": user_message,
            "pipeline_conversation": pipeline_conversation,
            "pipeline_context": self.pipeline_context,
        }
        save_file(context, file_name=f"{file_name}_request_context_pipeline")

    def export(self, file_name: str = "dev"):
        self.export_user_context(file_name)
        self.export_pipeline_context(file_name)
        