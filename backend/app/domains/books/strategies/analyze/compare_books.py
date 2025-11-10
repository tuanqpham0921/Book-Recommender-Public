import logging


from app.common.messages import SystemMessage
from app.common.prompt_loader import format_prompt
from app.orchestration import RequestContext
from app.domains.books.schemas import (
    CompareStrategy,
)
from .base import StrategyBase

logger = logging.getLogger(__name__)


# -------------------------------------------------------------------------------
class CompareBooks(StrategyBase):
    async def __call__(
        self, task: CompareStrategy, dependent_results, request_context: RequestContext
    ):
        await request_context.sse_stream.send_ui_loading("Comparing books...")
        logger.debug("Executing compare books strategy for task %s", task.id)

        sse_stream = request_context.sse_stream
        llm_client = request_context.llm_client

        # Use dependent_results instead of results parameter
        dependent_books = list(dependent_results.values())
        books_data = self._format_books_for_llm(dependent_books)

        # Extract comparison criteria from task
        comparison_criteria = task.comparison_criteria

        # Build similarity basis section conditionally
        similarity_basis_section = ""
        if hasattr(self, "similarity_basis") and self.similarity_basis:
            similarity_basis_section = f"- Similarity Basis: {', '.join([basis.value for basis in self.similarity_basis])}"

        # Load and format prompt from external file
        comparison_fields = comparison_criteria or "general characteristics"
        prompt = format_prompt(
            "books/compare_books_response.txt",
            books_data=books_data,
            comparison_fields=comparison_fields,
            similarity_basis_section=similarity_basis_section,
        )

        # Import locally to avoid circular import
        from app.clients.schemas import OpenAIRequest

        req = OpenAIRequest(
            system=SystemMessage(content=prompt),
            messages=[],
            sse_stream=sse_stream,
            temperature=0.5,
            top_p=0.3,
        )

        rag_response = await llm_client.execute(req)
        request_context.add_message(rag_response)

        # stream books
        await self._stream_books(dependent_books, sse_stream)
        await sse_stream.send_divider()
