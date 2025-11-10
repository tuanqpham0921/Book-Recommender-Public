import logging
import asyncio
import json
import time

from app.common.prompt_loader import format_prompt, load_prompt

from app.orchestration import RequestContext
from app.domains.books.schemas import (
    RetrievalTask,
)
from app.common.messages import SystemMessage, ToolMessage

logger = logging.getLogger(__name__)

from pydantic import BaseModel, Field
from openai import pydantic_function_tool

class llm_parse(BaseModel):
    
    accepted: bool = Field(..., description="Do we accept the retrieval methods")
    ui_message: str = Field(..., description="what to send to the user about our retrieval results")

    async def __call__(self):
        return {
            "accepted": self.accepted,
            "ui_message": self.ui_message
        }


class RetrievalBase:
    """Base class for all retrieval strategy implementations."""

    async def __call__(
        self, 
        task: RetrievalTask, 
        dependent_results, 
        request_context: RequestContext
    ):
        """
        Execute the retrieval strategy.

        Args:
            task: The task object containing retrieval parameters
            dependent_results: Results from dependent tasks (usually empty for retrievals)
            request_context: Context containing book_store, etc.
        """
        raise NotImplementedError("Subclasses must implement __call__")
    
    async def _handle_tool_call(
        self, tool_calls, max_calls: int = 10, **extra_kwargs
    ) -> list[ToolMessage]:
        """call the tool and return the message"""
        results = []
        for tool_call in tool_calls[:max_calls]:
            try:

                tool_name = tool_call.function.name
                tool_id = tool_call.id
                logger.info(f"🔧 Starting tool call: {tool_name} (id: {tool_id})")

                raw_args = json.loads(tool_call.function.arguments)
                tool_instance = tool_call.function.parsed_arguments

                start = time.monotonic()
                # logger.info(f"⚡ Executing {tool_name} with args: {raw_args}")
                logger.info(f"⚡ Executing {tool_name}")

                result = await tool_instance(**extra_kwargs)
                elapsed = round(time.monotonic() - start, 2)

                logger.info(f"✅ Tool {tool_name} completed successfully in {elapsed}s")

                results.append(
                    ToolMessage(
                        name=tool_call.function.name,
                        tool_call_id=tool_call.id,
                        content=result,
                        elapsed=elapsed,
                    )
                )
            except json.JSONDecodeError as e:
                logger.error(f"🛑 JSON parsing failed for tool {tool_name}: {e}")
                continue
            except Exception as e:
                logger.error(
                    f"🛑 Tool execution failed for {tool_name}: {e}", exc_info=True
                )
                continue

        return results
    
    async def retrieval_post_processing(
        self, 
        results, 
        task: RetrievalTask, 
        request_context: RequestContext
    ):
        # Import locally to avoid circular import
        from app.clients.schemas import OpenAIRequest

        tool_name = llm_parse.__name__
        tool = pydantic_function_tool(
            llm_parse,
            name=tool_name,
            description=f"Fill the schema for {tool_name}",
        )
        tool_choice = {"type": "function", "function": {"name": tool_name}}

        format_books = self._format_books_for_llm([results])
        format_task = task.model_dump_json()
        
        from app.config.constants import BookConstraints
        
        prompt = format_prompt(
            prompt_path="books/retrieval_post_processing.txt",
            in_domain_msg=str(request_context.pipeline_context["in_domain_message"]),
            filter_criteria=str(format_task),
            book_results=str(format_books),
            book_constraints=str(BookConstraints()),
        )

        # Create request for LLM
        req = OpenAIRequest(
            system=SystemMessage(content=prompt),
            messages=[],
            tools=[tool],
            tool_choice=tool_choice,
            temperature=0.7,  # Higher creativity for recommendations
            top_p=0.8,
        )
        
        assistant_msg = await request_context.llm_client.execute(req)

        # this shouldn't happen at all but raise to be safe
        if not assistant_msg or not assistant_msg.tool_calls:
            raise RuntimeError(f"🛑 {tool_name} parse {tool_name} FAILED")

        # Add to pipeline conversation (internal)
        request_context.add_message(assistant_msg)
        tool_message = await self._handle_tool_call(
            assistant_msg.tool_calls, max_calls=1
        )
        
        await request_context.sse_stream.send_chars(tool_message[0].content["ui_message"])
        return tool_message[0].content["accepted"]

    
    
    def _format_books_for_llm(self, results):
        """Format books for LLM readability."""
        logger.debug("Formatting %d book results for LLM", len(results))

        formatted = []
        for result in results:
            if isinstance(result, str):
                formatted.append(result + "\n")
                continue

            for i, book in enumerate(result):
                book_text = f"""Book {i+1}: "{book.get('title', 'Unknown')}"
- Author(s): {book.get('authors', 'Unknown')}
- Categories: {book.get('categories', 'Unknown')}
- Published: {book.get('published_year', 'Unknown')}
- Rating: {book.get('average_rating', 'N/A')}/5
- Pages: {book.get('num_pages', 'N/A')}
- ISBN: {book.get('isbn13', 'N/A')}"""
                formatted.append(book_text)

        return "\n\n".join(formatted)

    async def _stream_books(self, results, sse_stream):
        """Stream book cards to frontend."""
        # await sse_stream.send_json({"type": "books_start", "total": len(results)})
        sent_isbn = set()
        for result in results:
            if isinstance(result, str):
                continue

            for i, book_dict in enumerate(result):
                if book_dict["isbn13"] in sent_isbn:
                    continue

                await sse_stream.send_json(
                    {"type": "book_card", "position": i, "data": book_dict}
                )
                await asyncio.sleep(0.2)  # Smooth streaming
                sent_isbn.add(book_dict["isbn13"])
        