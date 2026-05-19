"""Backfill description embeddings for books missing vectors."""
from tqdm import tqdm
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from clients.openai_client import OpenAIClient
from db.schema import BookModel
from ingestion.store import iter_missing_books


def embedding_text(book: dict) -> str:
    """Canonical text used for book description embeddings."""
    return f"{book['title']}\n\n{book['description']}"

async def get_num_book_missing_embeddings(
    session_factory: async_sessionmaker[AsyncSession],
) -> int:
    """Get the number of books that are missing embeddings."""
    stmt = (
        select(func.count())
        .select_from(BookModel)
        .where(BookModel.embedding.is_(None))
        .where(BookModel.description.is_not(None))  # match iter_missing_books
    )
    async with session_factory() as session:
        result = await session.execute(stmt)
        return result.scalar_one()

async def update_book_embedding(
    book: dict,
    openai_client: OpenAIClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Compute an embedding and persist only the embedding column."""
    embedding = await openai_client.get_embedding(embedding_text(book))
    stmt = (
        update(BookModel)
        .where(BookModel.isbn13 == book["isbn13"])
        .values(embedding=embedding)
    )
    async with session_factory() as session:
        await session.execute(stmt)
        await session.commit()


async def embed_missing_books(
    session_factory: async_sessionmaker[AsyncSession],
    openai_client: OpenAIClient,
) -> int:
    """Backfill embeddings for rows where embedding IS NULL."""
    num_missing = await get_num_book_missing_embeddings(session_factory)
    if num_missing == 0:
        print("No books missing embeddings")
        return 0

    count = 0
    with tqdm(desc="Embedding books", unit="book", total=num_missing) as pbar:
        async for book in iter_missing_books(session_factory):
            await update_book_embedding(book, openai_client, session_factory)
            pbar.update(1)
            count += 1

    print(f"✅ Embedded {count} books")
    return count
