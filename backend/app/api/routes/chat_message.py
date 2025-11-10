import logging
import asyncio

from sse_starlette.sse import EventSourceResponse
from fastapi import APIRouter, HTTPException, Depends

from app.api.schemas import ChatIn
from app.common.messages import UserMessage
from app.orchestration.orchestrator import Orchestrator

from app.api.dependencies import get_orchestrator, get_request_context_factory

logger = logging.getLogger(__name__)
# Store assistant instances to access book results
router = APIRouter(tags=["Chat"])


@router.post("/session/{session_id}/message")
async def chat(
    session_id: str,
    chat_in: ChatIn,
    orchestrator: Orchestrator = Depends(get_orchestrator),
    create_context=Depends(get_request_context_factory),
):
    """Send a message to a session with SSE response."""
    if not chat_in.message or not chat_in.message.strip():
        raise HTTPException(status_code=400, detail="Message is required")
    
    if len(chat_in.message) > 2000:
        raise HTTPException(
            status_code=400, 
            detail=f"Message is too long. Maximum {2000} characters allowed."
        )
    
    try:
        user_message = UserMessage(content=chat_in.message)

        async def generate_chat_response():
            try:
                # Create SSE stream inside the generator
                from app.common.sse_stream import SSEStream

                sse_stream = SSEStream()

                logger.info(f"🚀 Starting chat for session: {session_id}")

                # Create request context using factory
                request_context = create_context(session_id, user_message, sse_stream)

                try:
                    # Start orchestrator in background task
                    orchestrator_task = asyncio.create_task(
                        orchestrator.run(request_context)
                    )

                    # Stream events as they come
                    async for event in sse_stream:
                        yield event

                    # Wait for orchestrator to complete
                    await orchestrator_task

                except Exception as e:
                    logger.exception(f"❌ Orchestration error at endpoint: {e}")
                    # await sse_stream.send_error(f"Endpoint orchestration error: {str(e)}")
                    await sse_stream.send_error(f"Um... something went wrong with the network endpoint.")
                finally:
                    logger.info("🔚 Endpoint cleanup: closing SSE stream")
                    await sse_stream.close()
                    

            except Exception as e:
                logger.exception(f"❌ Failed to create SSE stream: {e}")
                yield {
                    "event": "error",
                    "data": f'{{"error": "No... failed to initialize your request"}}',
                }

        return EventSourceResponse(
            generate_chat_response(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                # "Connection": "keep-alive",
            },
        )

    except Exception as e:
        logger.exception("❌ Chat error")
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")
