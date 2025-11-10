import time
import logging

from openai import AsyncOpenAI
from typing import List, Optional

from .schemas import OpenAIRequest
from .base import BaseLLMClient

from app.config import settings
from app.common.messages import AssistantMessage, SystemMessage, UserMessage
from app.common.sse_stream import SSEStream
from app.common.utils import print_json

logger = logging.getLogger(__name__)


class OpenAIClient(BaseLLMClient):
    """
    Async client for OpenAI API with streaming support.
    """

    def __init__(
        self,
        api_key: str,
    ):
        self.client = AsyncOpenAI(api_key=api_key)

    async def get_embedding(
        self,
        input,
        model=settings.openai.EMBEDDING_MODEL,
        dimensions=settings.openai.EMBEDDING_DIMENSIONS,
    ):
        """
        Generate embeddings for input text.

        Args:
            input: Text to embed
            model: Embedding model name
            dimensions: Embedding vector dimensions

        Returns:
            Embedding vector
        """
        res = await self.client.embeddings.create(
            input=input, model=model, dimensions=dimensions
        )
        return res.data[0].embedding

    async def estimate_tokens(self, payload) -> int:
        """Estimate token count for payload (not implemented)."""
        pass

    async def execute(self, req: OpenAIRequest) -> AssistantMessage:
        """
        Execute chat completion request with optional streaming.

        Args:
            req: OpenAI request configuration

        Returns:
            AssistantMessage with response content and metadata
        """
        try:
            payload = req.to_payload()

            start = time.monotonic()
            final_completion = await self._chat_stream(payload, req.sse_stream)
            elapsed = round(time.monotonic() - start, 2)

            response_message = final_completion.choices[0].message
            assistant_msg = AssistantMessage(
                id=final_completion.id,
                content=response_message.content,
                tool_calls=response_message.tool_calls,
                refusal=response_message.refusal,
                elapsed=elapsed,
            )

            return assistant_msg
        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}")
            raise e

    async def _chat_stream(self, payload: dict, sse_stream: Optional[SSEStream]):
        """
        Stream chat completion and send deltas to SSE stream if provided.

        Args:
            payload: OpenAI API payload
            sse_stream: Optional SSE stream for real-time updates

        Returns:
            Final completion message
        """
        async with self.client.beta.chat.completions.stream(**payload) as stream:
            async for event in stream:
                if event.type == "content.delta" and sse_stream:
                    await sse_stream.send_chars(data=event.delta)

            final_completion = await stream.get_final_completion()

        return final_completion

    async def close(self):
        """Close the underlying HTTP client."""
        await self.client._client.aclose()

    async def _smoke_api_call(self, sse_stream: SSEStream):
        """
        Test OpenAI API connectivity with a simple call.

        Args:
            sse_stream: Stream for status updates

        Returns:
            True if API is responsive
        """
        await sse_stream.send_ui_loading("Smoke screening openAI...")

        system_message = SystemMessage(
            content="Tell me if you are here! Answer with a single word: yes or no."
        )
        chat_messages = UserMessage(content="Hello are you there?")
        req = OpenAIRequest(
            system=system_message,
            messages=[chat_messages],
            temperature=0.0,
            top_p=1.0,
            max_tokens=50,
            sse_stream=sse_stream,
        )

        response = await self.execute(req)
        return response.content.strip().lower() == "yes"
