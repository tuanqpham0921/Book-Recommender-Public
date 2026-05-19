from typing import Optional
from pydantic import BaseModel
from abc import ABC, abstractmethod
from pydantic import BaseModel
from typing import Optional, Any


class BaseLLMRequest(BaseModel, ABC):
    """Base schema for any LLM request (OpenAI, Anthropic, etc.)."""

    model: str
    temperature: float = 0.3
    top_p: float = 0.8
    sse_stream: Optional[Any] = None

    # Trimming + runtime
    max_prompt_tokens: int = 120_000
    reserved_output_tokens: int = 4_000
    # trim_strategy: Literal["recency", "summary", "domain"] = "recency"

    # Internal metadata
    # request_id: Optional[str] = None

    @abstractmethod
    def to_payload(self) -> dict[str, Any]:
        """Convert this request to provider-specific API payload."""
        ...

class BaseLLMClient(ABC):
    """Abstract base interface for all LLM providers."""

    max_tokens: int = 100_000

    @abstractmethod
    async def execute(self, req: BaseLLMRequest):
        """Execute a request (stream or not) and return an AssistantMessage."""
        ...

    @abstractmethod
    async def close(self):
        """Close any resources used by the client."""
        ...
        
    def token_count(self, text: str) -> int:
        """Count the number of tokens in the text."""
        import tiktoken
        encoding = tiktoken.encoding_for_model(self.embedding_model)
        return len(encoding.encode(text))
    
    def over_max_tokens(self, token_count: int) -> bool:
        return token_count > self.max_tokens