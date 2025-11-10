import logging

from app.orchestration import RequestContext
from app.domains.books.schemas import (
    FindByTitleRetrieval,
)
from .base import RetrievalBase

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------


class FindByTitle(RetrievalBase):
    async def __call__(
        self,
        task: FindByTitleRetrieval,
        dependent_results,
        request_context: RequestContext,
    ):
        # Extract title from task data
        await request_context.sse_stream.send_ui_loading("Getting Book By Title...")
        
        book_title = task.title
        if not book_title:
            return f"No title provided in task: {task.id}"

        results = await request_context.book_store.search_by_title(title=book_title, authors=task.authors)
        accepted = await self.retrieval_post_processing(results, task, request_context)
        
        if accepted:
            await self._stream_books([results], request_context.sse_stream)
            await request_context.sse_stream.send_divider()

            return results[:1]
        
        await request_context.sse_stream.send_divider()
        return f"Unable to find book title {book_title}"