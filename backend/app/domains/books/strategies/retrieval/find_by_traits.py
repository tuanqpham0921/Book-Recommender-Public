import logging

from app.orchestration import RequestContext
from app.domains.books.schemas import (
    FindByTraitsRetrieval,
)

logger = logging.getLogger(__name__)
from .base import RetrievalBase

# --------------------------------------------------------------------------

# TODO: I need to make sure that this send out a response or something
class FindByTraits(RetrievalBase):
    async def __call__(
        self,
        task: FindByTraitsRetrieval,
        dependent_results,
        request_context: RequestContext | None,
    ):
        await request_context.sse_stream.send_ui_loading("Getting Book By Traits...")        
        # Extract search criteria and filters from task data
        search_criteria = task.search_criteria
        filters = task.filters
        if not filters:
            return f"No filter provided in task: {task.id}"
        
        # TODO: we can add this to the operation results later
        if filters.authors and len(filters.authors) > filters.limit:
            logger.warning(f"⚠️ There are more authors than the requested limit. Exapnding the limit")
        
        if filters.exclusion:
            logger.warning(f"⚠️ Don't have exclusion implmented. Procedding without exclusion feature")


        results = await request_context.book_store.search_by_book_filter(filters)
        accepted = await self.retrieval_post_processing(results, task, request_context)

        if accepted:
            # await request_context.sse_stream.send_chars("Awsome I found some books on for traits: ")
            await self._stream_books([results], sse_stream=request_context.sse_stream)
            await request_context.sse_stream.send_divider()
            return results
        
        await request_context.sse_stream.send_divider()
        return f"Unable to find books for criteria task: {task.id} with filters: {filters.model_dump()}"