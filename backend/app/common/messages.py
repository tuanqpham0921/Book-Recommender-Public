import json

from pytz import UTC
from datetime import datetime
from typing_extensions import Annotated
from pydantic import BaseModel, Field
from openai.types.chat import ParsedFunctionToolCall
from typing import Union, Dict, Optional, List, Literal, Any

from app.common.enums import Role


class BaseMessage(BaseModel):
    def to_openai_dict(self) -> Dict:
        raise NotImplementedError


# --- Role-specific Messages ---
class SystemMessage(BaseMessage):
    role: Literal[Role.SYSTEM] = Role.SYSTEM
    content: str

    def to_openai_dict(self) -> Dict:
        return {"role": self.role, "content": self.content}


class UserMessage(BaseMessage):
    role: Literal[Role.USER] = Role.USER
    content: str
    created: Optional[str] = Field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )

    def to_openai_dict(self) -> Dict:
        return {"role": self.role, "content": self.content}


class AssistantMessage(BaseMessage):
    role: Literal[Role.ASSISTANT] = Role.ASSISTANT
    id: Optional[str] = None
    content: Optional[str] = None
    tool_calls: Optional[List[ParsedFunctionToolCall]] = None
    elapsed: Optional[float] = None
    refusal: Optional[str] = None
    created: Optional[str] = Field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )

    def to_openai_dict(self) -> Dict:
        base = {"role": self.role}
        if self.content:
            base["content"] = self.content
        if self.tool_calls:
            # convert each tool call to OpenAI schema (list of dicts)
            base["tool_calls"] = [tc.model_dump(exclude=None) for tc in self.tool_calls]
        return base


class ToolMessage(BaseMessage):
    role: Literal[Role.TOOL] = Role.TOOL
    name: str
    tool_call_id: str
    content: Any  # tool results only (raw output)
    elapsed: Optional[float] = None
    created: Optional[str] = Field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )

    def to_openai_dict(self) -> Dict:
        # OpenAI tool messages require string content and no extra fields like name/elapsed
        content = self.content
        if isinstance(content, (dict, list)):
            content = json.dumps(content)
        else:
            content = str(content)

        return {
            "role": self.role,
            "tool_call_id": self.tool_call_id,
            "content": content,
        }


# --- Discriminated Union of Messages ---
APIMessage = Annotated[
    Union[SystemMessage, UserMessage, AssistantMessage, ToolMessage],
    Field(discriminator="role"),
]
