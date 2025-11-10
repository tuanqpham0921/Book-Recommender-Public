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
                "render_postcompile": True  # Handles modern SQLAlchemy features
            }
        )
        return str(compiled)
    except Exception as e:
        # Fallback without literal binds if that fails
        return str(stmt.compile())

def build_title_search(model, book_title: str, authors: list[str] = None, limit: int = 1, similarity_threshold: float = 0.7):
    """Apply title-based filtering with similarity search."""
    stmt = select(model)
    stmt = stmt.where(
        or_(
            model.title.ilike(f"%{book_title}%"),
            func.similarity(model.title, text(f"'{book_title}'")) > similarity_threshold,
        )
    )
    if authors:
        for author in authors:
            stmt = stmt.where(
                model.authors.ilike(f"%{author}%")
            )
    
    stmt = stmt.order_by(func.similarity(model.title, text(f"'{book_title}'")).desc())
    stmt = stmt.limit(limit)
    return stmt


def build_isbn_search(model, isbn13: str):
    """Apply ISBN-based filtering."""
    stmt = select(model)
    stmt = stmt.where(
        or_(model.isbn13 == isbn13)  # Also check isbn10 field
    )
    return stmt


def build_author_search(model, author_name: str, similarity_threshold: float = 0.3):
    """Apply author-based filtering."""
    stmt = select(model)
    stmt = stmt.where(
        or_(
            model.author.ilike(f"%{author_name}%"),
            func.similarity(model.authors, text(f"'{author_name}'")) > similarity_threshold,
        )
    )
    stmt = stmt.order_by(func.similarity(model.author, text(f"'{author_name}'")).desc())
    return stmt


def build_filtered_search(
    model, 
    filters: BooksFilter, 
    similarity_threshold: float = 0.3,
    # to ensure we don't overload the query
    fuzzy_limit: int = 10 
):
    """Build a filtered search stmt."""
    stmt = select(model)
    conditions = []
    
    # Text search if provided
    if filters.keywords:
        for keywords in filters.keywords[:fuzzy_limit]:
            text_condition = or_(
                model.title.ilike(f"%{keywords}%"),
                model.authors.ilike(f"%{keywords}%"),
                model.description.ilike(f"%{keywords}%")
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
                    func.similarity(model.authors, text(f"'{name}'")) > similarity_threshold,
                )
            )
            author_names.append(name)
        # Find books by ANY of the specified authors
        conditions.append(or_(*author_conditions))
        
    if filters.categories:
        category_conditions = [
            model.categories.ilike(f"%{cat}%") 
            for cat in filters.categories[:fuzzy_limit]
        ]
        conditions.append(or_(*category_conditions))
    
    if filters.genre:
        conditions.append(model.genre.like(f"%{filters.genre}%"))
    
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
            stmt = stmt.order_by(func.similarity(model.authors, text(f"'{name}'")).desc())
    
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

# ---------------------------------------------------------------------

def build_embedding_search(
    model,
    query_embedding: List[float],
    filters: Optional[BooksFilter] = None,
    similarity_threshold: float = 0.7,
    limit: int = 50,
    embedding_column: str = "embedding"
):
    """Build embedding similarity search query."""
    
    # Get the embedding column
    embed_col = getattr(model, embedding_column)
    
    # Base query with cosine similarity
    stmt = select(
        model,
        # Calculate cosine similarity (1 - cosine distance)
        (1 - embed_col.cosine_distance(query_embedding)).label('similarity_score')
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
        conditions = []
        
        if filters.authors:
            author_conditions = [model.authors.ilike(f"%{author}%") for author in filters.authors]
            conditions.append(or_(*author_conditions))
        
        if filters.categories:
            category_conditions = [
                model.categories.ilike(f"%{cat}%") 
                for cat in filters.categories
            ]
            conditions.append(or_(*category_conditions))
        
        if filters.min_rating:
            conditions.append(model.average_rating >= filters.min_rating)
        
        if filters.max_pages:
            conditions.append(model.num_pages <= filters.max_pages)
        
        if filters.min_pages:
            conditions.append(model.num_pages >= filters.min_pages)
        
        # Apply conditions
        if conditions:
            stmt = stmt.where(and_(*conditions))
    
    # Order by similarity score (highest first)
    stmt = stmt.order_by(text('similarity_score DESC'))
    
    # Apply limit
    stmt = stmt.limit(limit)
    
    return stmt