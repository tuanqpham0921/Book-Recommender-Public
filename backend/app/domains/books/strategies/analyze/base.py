import logging
import asyncio


from app.orchestration import RequestContext
from app.domains.books.schemas import (
    AnalyzeTask,
)

logger = logging.getLogger(__name__)


class StrategyBase:
    """Base class for all strategy implementations."""

    async def __call__(
        self, task: AnalyzeTask, dependent_results, request_context: RequestContext
    ):
        """
        Execute the strategy.

        Args:
            task: The task object containing strategy parameters
            dependent_results: Results from dependent tasks
            request_context: Context containing llm_client, sse_stream, etc.
        """
        raise NotImplementedError("Subclasses must implement __call__")

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
