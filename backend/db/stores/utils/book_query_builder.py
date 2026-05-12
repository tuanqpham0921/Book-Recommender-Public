"""Query builder for book-related database operations."""

from sqlalchemy import select, func, or_, and_, text
from app.domains.books.schemas.request_schemas import BooksFilter
from typing import Optional, List


def compile_sql(stmt):
    """Compile SQLAlchemy statement to actual SQL string with formatting."""
    try:
        # Compile with literal binds to show actual values
        compiled = stmt.compile(
            compile_kwargs={
                "literal_binds": True,  # Shows actual parameter values
                "render_postcompile": True,  # Handles modern SQLAlchemy features
            }
        )
        return str(compiled)
    except Exception as e:
        # Fallback without literal binds if that fails
        return str(stmt.compile())


def build_title_search(
    model,
    book_title: str,
    authors: list[str] = None,
    limit: int = 1,
    similarity_threshold: float = 0.7,
):
    """Apply title-based filtering with similarity search."""
    stmt = select(model)
    stmt = stmt.where(
        or_(
            model.title.ilike(f"%{book_title}%"),
            func.similarity(model.title, text(f"'{book_title}'"))
            > similarity_threshold,
        )
    )
    if authors:
        for author in authors:
            stmt = stmt.where(model.authors.ilike(f"%{author}%"))

    stmt = stmt.order_by(func.similarity(model.title, text(f"'{book_title}'")).desc())
    stmt = stmt.limit(limit)
    return stmt


def build_isbn_search(model, isbn13: str):
    """Apply ISBN-based filtering."""
    stmt = select(model)
    stmt = stmt.where(or_(model.isbn13 == isbn13))  # Also check isbn10 field
    return stmt


def build_author_search(model, author_name: str, similarity_threshold: float = 0.3):
    """Apply author-based filtering."""
    stmt = select(model)
    stmt = stmt.where(
        or_(
            model.author.ilike(f"%{author_name}%"),
            func.similarity(model.authors, text(f"'{author_name}'"))
            > similarity_threshold,
        )
    )
    stmt = stmt.order_by(func.similarity(model.author, text(f"'{author_name}'")).desc())
    return stmt


def apply_book_filters(
    stmt,
    model,
    filters: BooksFilter,
    similarity_threshold: float = 0.3,
    fuzzy_limit: int = 10,
):
    """Apply book filters to an existing SQLAlchemy statement.

    Args:
        stmt: Base SQLAlchemy select statement
        model: SQLAlchemy model class
        filters: BooksFilter object with filter criteria
        similarity_threshold: Minimum similarity score for fuzzy matching
        fuzzy_limit: Maximum number of items to process for fuzzy matching

    Returns:
        Modified SQLAlchemy statement with filters applied
    """
    conditions = []
    author_names = []
    category_names = []

    # Text search if provided
    if filters.keywords:
        for keywords in filters.keywords[:fuzzy_limit]:
            text_condition = or_(
                model.title.ilike(f"%{keywords}%"),
                model.authors.ilike(f"%{keywords}%"),
                model.description.ilike(f"%{keywords}%"),
            )
            conditions.append(text_condition)

    # Author filtering
    if filters.authors:
        author_conditions = []
        author_names = []
        for name in filters.authors[:fuzzy_limit]:
            author_conditions.append(
                or_(
                    model.authors.ilike(f"%{name}%"),
                    func.similarity(model.authors, text(f"'{name}'"))
                    > similarity_threshold,
                )
            )
            author_names.append(name)
        # Find books by ANY of the specified authors
        conditions.append(or_(*author_conditions))

    if filters.categories:
        category_conditions = []
        category_names = []
        for cat in filters.categories[:fuzzy_limit]:
            category_conditions.append(
                or_(
                    model.categories.ilike(f"%{cat}%"),
                    func.similarity(model.categories, text(f"'{cat}'"))
                    > similarity_threshold,
                )
            )
            category_names.append(cat)
        # Find books by ANY of the specified authors
        conditions.append(or_(*category_conditions))

    if filters.genre:
        conditions.append(model.genre.ilike(f"%{filters.genre.value}%"))

    if filters.min_pages:
        conditions.append(model.num_pages >= filters.min_pages)

    if filters.max_pages:
        conditions.append(model.num_pages <= filters.max_pages)

    if filters.min_year:
        conditions.append(model.published_year >= filters.min_year)

    if filters.max_year:
        conditions.append(model.published_year <= filters.max_year)

    if filters.min_rating:
        conditions.append(model.average_rating >= filters.min_rating)

    if filters.max_rating:
        conditions.append(model.average_rating <= filters.max_rating)

    # Apply all conditions
    if conditions:
        stmt = stmt.where(and_(*conditions))

    if filters.authors:
        for name in author_names:
            stmt = stmt.order_by(
                func.similarity(model.authors, text(f"'{name}'")).desc()
            )

    if filters.categories:
        for cat in category_names:
            stmt = stmt.order_by(
                func.similarity(model.categories, text(f"'{cat}'")).desc()
            )

    # Apply sorting
    if filters.sort_by:
        sort_column = getattr(model, filters.sort_by, model.title)
        if filters.sort_order == "desc":
            stmt = stmt.order_by(sort_column.desc())
        else:
            stmt = stmt.order_by(sort_column.asc())
    else:
        stmt = stmt.order_by(model.average_rating.desc().nulls_last())

    # Apply limit
    stmt = stmt.limit(filters.limit or 3)

    return stmt


def build_filtered_search(
    model,
    filters: BooksFilter,
    similarity_threshold: float = 0.3,
    fuzzy_limit: int = 10,
):
    """Build a filtered search query using apply_book_filters."""
    stmt = select(model)
    return apply_book_filters(stmt, model, filters, similarity_threshold, fuzzy_limit)


# ---------------------------------------------------------------------


def build_embedding_search(
    model,
    query_embedding: List[float],
    filters: Optional[BooksFilter] = None,
    similarity_threshold: float = 0.7,
    limit: int = 50,
    embedding_column: str = "embedding",
):
    """Build embedding similarity search query with optional filters."""

    # Get the embedding column
    embed_col = getattr(model, embedding_column)

    # Base query with cosine similarity
    stmt = select(
        model,
        # Calculate cosine similarity (1 - cosine distance)
        (1 - embed_col.cosine_distance(query_embedding)).label("similarity_score"),
    ).where(
        # Only include books with embeddings
        embed_col.is_not(None)
    )
    # ).filter(
    #     # Similarity threshold
    #     # embed_col.cosine_distance(query_embedding) < (1 - similarity_threshold)
    # )
    
    # Apply additional filters if provided
    if filters:
        # Temporarily remove limit from filters to apply it after sorting by similarity
        original_limit = filters.limit
        filters.limit = None

        # Apply all book filters
        stmt = apply_book_filters(
            stmt,
            model,
            filters,
            similarity_threshold=similarity_threshold,
            fuzzy_limit=10,
        )

        # Restore original limit
        filters.limit = original_limit

    # Order by similarity score (highest first) - this takes precedence
    stmt = stmt.order_by(text("similarity_score DESC"))

    # Apply limit
    stmt = stmt.limit(limit)

    return stmt
