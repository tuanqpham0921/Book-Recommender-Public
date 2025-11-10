import logging

from typing import List

from app.common.messages import SystemMessage
from app.common.prompt_loader import format_prompt
from app.orchestration import RequestContext
from app.domains.books.schemas import (
    RecommendationStrategy,
)
from app.domains.books.schemas.request_schemas import BooksFilter
from .base import StrategyBase

logger = logging.getLogger(__name__)


class RecommendBooks(StrategyBase):
    async def __call__(
        self,
        task: RecommendationStrategy,
        dependent_results: dict,
        request_context: RequestContext,
    ):
        await request_context.sse_stream.send_ui_loading("Find Book Recommendations...")
        logger.debug(
            "Executing recommendation strategy for task %s with semantic input: %s",
            task.id,
            task.semantic_input,
        )

        sse_stream = request_context.sse_stream
        semantic_input = task.semantic_input
        filters = task.filters or BooksFilter()

        # Step 1: Get reference books context
        dependent_books = list(dependent_results.values())

        query_texts = await self._get_embedding(
            semantic_input, dependent_books, request_context
        )

        # Step 2: Get candidate books from database (broader search)
        candidate_books = []
        if query_texts:
            for query in query_texts:
                result = await self._get_candidate_books(filters, query, request_context)

                if result:
                    candidate_books.extend(result)
        else:
            result = await request_context.book_store.search_by_book_filter(filters)
            if result:
                    candidate_books.extend(result)

        # Step 3: Use LLM for semantic recommendation
        book_data = self._format_books_for_llm(dependent_books)
        recommended_books = await self._get_semantic_recommendations(
            request_context=request_context,
            semantic_input=semantic_input,
            book_data=book_data,
            candidate_books=candidate_books,
            limit=filters.limit or 10,
        )

        # Step 4: Stream results
        if recommended_books:
            dependent_books.append(recommended_books)
        await self._stream_books(dependent_books, sse_stream)

        return recommended_books

    async def _get_embedding(
        self, semantic_input: str, dependent_books, request_context: RequestContext
    ):
        """Use LLM to generate an embedding using the description for search"""
        if not dependent_books:
            return [semantic_input]

        from app.clients.schemas import OpenAIRequest

        llm = request_context.llm_client

        results = set()
        for dep in dependent_books:
            if isinstance(dep, str):
                continue

            # Consider batching multiple embeddings in a single API call for performance
            for book in dep:
                book_data = self._format_books_for_llm([[book]])

                # Build the recommendation prompt
                prompt = format_prompt(
                    "books/generate_search_query.txt",
                    semantic_input=semantic_input,
                    reference_books=book_data,
                )

                # Create request for LLM
                req = OpenAIRequest(
                    system=SystemMessage(content=prompt),
                    messages=[],
                    temperature=0.7,
                    top_p=0.8,
                )

                # Get LLM response
                rag_response = await llm.execute(req)
                request_context.add_message(rag_response)

                query_text = (
                    rag_response.content if rag_response.content else semantic_input
                )

                results.add(query_text)

                logger.debug("Generated query text: %s", query_text)

        return list(results)

    async def _get_candidate_books(
        self, filters: BooksFilter, query_text: str, request_context: RequestContext
    ) -> List[dict]:
        """Get a broader set of candidate books for semantic analysis."""
        # Create a looser filter for getting candidates

        llm = request_context.llm_client
        book_store = request_context.book_store

        query_embedding = await llm.get_embedding(query_text)

        logger.debug("Generated embedding with %d dimensions", len(query_embedding))

        # Perform semantic search using the generated embedding
        # get the books and stuff and embedding search set up

        candidate_filter = filters.model_copy(
            update={
                "limit": 5,  # Get more candidates for LLM to choose from
                # Keep user's explicit filters but remove restrictive ones for broader search
                # "min_rating": filters.min_rating or 3.0,  # Only reasonably rated books
            }
        )

        # If no specific constraints, get diverse books
        if not any(
            [filters.authors, filters.categories, filters.genre, filters.keywords]
        ):
            candidate_filter.limit = 10  # Cast wider net

        candidates = await book_store.search_by_embedding(
            query_embedding, candidate_filter
        )

        return candidates

    async def _get_semantic_recommendations(
        self,
        request_context: RequestContext,
        semantic_input: str,
        book_data: str,
        candidate_books: list[dict],
        limit: int = 10,
    ) -> List[dict]:
        """Use LLM to semantically match books based on input and references."""

        llm_client = request_context.llm_client
        sse_stream = request_context.sse_stream

        # Format candidate books for LLM
        candidates_text = self._format_books_for_llm([candidate_books])

        # Build the recommendation prompt
        prompt = format_prompt(
            "books/semantic_recommendation.txt",
            semantic_input=semantic_input,
            reference_books=book_data,
            candidate_books=candidates_text,
            max_recommendations=limit,
        )

        # Import locally to avoid circular import
        from app.clients.schemas import OpenAIRequest

        # Create request for LLM
        req = OpenAIRequest(
            system=SystemMessage(content=prompt),
            messages=[],
            sse_stream=sse_stream,
            temperature=0.7,  # Higher creativity for recommendations
            top_p=0.8,
        )

        # Get LLM response
        rag_response = await llm_client.execute(req)
        request_context.add_message(rag_response)

        # Parse LLM response to extract recommended book ISBNs/titles
        recommended_books = self._parse_llm_recommendations(
            rag_response.content, candidate_books
        )

        return recommended_books

    def _parse_llm_recommendations(
        self, llm_response: str, candidate_books: List[dict]
    ) -> List[dict]:
        """Parse LLM response to extract recommended books."""
        recommended_books = []

        # Create lookup dictionaries for easy matching
        books_by_isbn = {
            book.get("isbn13"): book for book in candidate_books if book.get("isbn13")
        }
        books_by_title = {
            book.get("title", "").lower(): book for book in candidate_books
        }

        # Look for ISBN patterns in the response
        import re

        isbn_pattern = r"\b\d{13}\b"  # 13-digit ISBN
        found_isbns = re.findall(isbn_pattern, llm_response)

        for isbn in found_isbns:
            if isbn in books_by_isbn:
                recommended_books.append(books_by_isbn[isbn])

        # If no ISBNs found, try to match by title
        if not recommended_books:
            lines = llm_response.split("\n")
            for line in lines:
                line_lower = line.lower()
                for title, book in books_by_title.items():
                    if title in line_lower and len(title) > 5:  # Avoid short matches
                        if book not in recommended_books:
                            recommended_books.append(book)
                        break

        return recommended_books
