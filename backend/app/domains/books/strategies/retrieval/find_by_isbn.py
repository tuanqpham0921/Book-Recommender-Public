import logging

from app.orchestration import RequestContext
from app.domains.books.schemas import (
    FindByISBN13Retrieval,
)

logger = logging.getLogger(__name__)
from .base import RetrievalBase

class FindByIsbn13(RetrievalBase):
    async def __call__(
        self,
        task: FindByISBN13Retrieval,
        dependent_results,
        request_context: RequestContext,
    ):
        await request_context.sse_stream.send_ui_loading("Getting Book By ISBN13...")
        
        # Extract ISBN from task data
        isbn13 = task.isbn13
        if not isbn13:
            return f"No ISBN13 provided in task: {task.id}"

        result = await request_context.book_store.get_by_isbn(isbn=isbn13)
        return result if result else f"Unable to find book isbn13: {isbn13}"