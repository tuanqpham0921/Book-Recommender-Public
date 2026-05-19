import time
import logging

from openai import AsyncOpenAI
from typing import List, Optional

from .schemas import OpenAIRequest
from .base import BaseLLMClient

from config.settings import OpenAISettings
from app.common.messages import AssistantMessage
from app.common.sse_stream import SSEStream

logger = logging.getLogger(__name__)

class OpenAIClient(BaseLLMClient):
    def __init__(self, openai_settings: OpenAISettings):
        """Initialize the OpenAIClient."""
        if not openai_settings.API_KEY:
            raise ValueError("OpenAI API key not set")
        
        self.client               = AsyncOpenAI(api_key=openai_settings.API_KEY)
        self.embedding_model      = openai_settings.EMBEDDING_MODEL
        self.embedding_dimensions = openai_settings.EMBEDDING_DIMENSIONS
        
    async def get_embedding(self, input: str) -> List[float]:
        """Get the embedding for the input text."""
        try:
            response = await self.client.embeddings.create(
                                input=input, 
                                model=self.embedding_model, 
                                dimensions=self.embedding_dimensions
                            )
            return response.data[0].embedding
        
        except Exception as e:
            logger.error(f"❌❌❌ OpenAI embedding API call failed: {e}")
            raise e
        
    async def get_embeddings_batch(self, input: List[str]) -> List[float]:
        """Get the embeddings for the input texts."""
        try:
            response = await self.client.embeddings.create(
                                input=input, 
                                model=self.embedding_model, 
                                dimensions=self.embedding_dimensions
                            )
            response_data = sorted(response.data, key=lambda x: x.index)
            return [data.embedding for data in response_data]
        except Exception as e:
            logger.error(f"❌❌❌ OpenAI embedding API call failed: {e}")
            raise e

    async def execute(self, req: OpenAIRequest) -> AssistantMessage:
        """Execute the chat completion."""
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

            # --- Execute ---
            return assistant_msg
        except Exception as e:
            logger.error(f"❌❌❌ OpenAI API call failed: {e}")
            raise e

    async def _chat_stream(self, payload: dict, sse_stream: Optional[SSEStream]):
        """Stream the chat completion."""
        async with self.client.beta.chat.completions.stream(**payload) as stream:
            async for event in stream:
                if event.type == "content.delta" and sse_stream:
                    await sse_stream.send_chars(data=event.delta)

            final_completion = await stream.get_final_completion()
            # print_json(final_completion.model_dump(), "Final Completion")

        # one section is done
        return final_completion

    async def close(self):
        """Close the OpenAIClient."""
        await self.client._client.aclose()
