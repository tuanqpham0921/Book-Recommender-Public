import os
import asyncio
import time
import pandas as pd

from db.schema import BookModel import BookModel
from clients.openai_client import OpenAIClient
from config import settings
from config.bootstrap import IngestionConstants
# TODO
# need to add function comments
# need to add optimizations
# need to stream the csv file? or make it better
# DETAIL:  Key (isbn13)=(9780002005883) already exists.

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from db import (
    close_async_engine, 
    get_async_engine, 
    get_session_factory,
    is_ready
)

def batchify(iterable, batch_size):
    """Split an iterable into batches of specified size."""
    for i in range(0, len(iterable), batch_size):
        yield iterable[i : i + batch_size]

def load_books_from_csv(path: str = settings.postgres.DATA_PATH, 
                        csv_file: str = IngestionConstants.CSV_FILE,
                        limit: int | None = IngestionConstants.APPROXIMATE_LOAD_LIMIT):
    """Load books from CSV.

    ``limit`` caps how many **CSV rows** are read (via ``head``), not how many
    valid books you end up with—rows missing title/description are skipped, so
    the book list can be smaller than ``limit``.
    """
    path = settings.postgres.DATA_PATH + csv_file
    if not os.path.exists(path):
        raise FileNotFoundError(f"File {path} does not exist")

    df = pd.read_csv(path)
    if limit is not None:
        df = df.head(limit)
        print(
            f"Considering only the first {limit} CSV rows (limit applies to rows, not books)"
        )
    else:
        print(f"Loading all {len(df)} rows")

    # Create book chunks for embedding
    return df


async def embed_batch(batch: list[dict], openai_client: OpenAIClient) -> list[dict]:
    """Embed a batch of books using OpenAI."""
    for book in batch:
        book.embedding = await openai_client.get_embedding(
            book.title + "\n\n" + book.description
        )

    return batch


async def embed_and_store_books(
    books: list[BookModel],
    session_factory: async_sessionmaker[AsyncSession],
    openai_client: OpenAIClient,
    batch_size: int = IngestionConstants.BATCH_SIZE,
):
    """Embed and store a batch of books into the database."""
    if not books:
        raise ValueError("❌ No books to embed and store")

    for batch in batchify(books, batch_size):
        print(f"Embedding batch {len(batch)} books")
        embedded_batch = await embed_batch(batch, openai_client)

        if not embedded_batch:
            continue

        try:
            async with session_factory() as session:
                session.add_all(embedded_batch)
                await session.commit()
            print(f"✅Committed batch {len(embedded_batch)} books")
        except Exception as e:
            print(f"❌ Error committing batch: {e}")
            raise

    return


async def load_books():
    """Main function to load books from CSV/Parquet into PostgreSQL."""
    async_engine = None
    openai_client = None
    try:
        async_engine = get_async_engine()
        session_factory = get_session_factory(async_engine)
        if await is_ready(session_factory):
            print("✅ Table exists, ready to use!")
            return
    
        print("Loading Books from CSV")
        books_df = load_books_from_csv()
        print(f"Loaded {len(books_df)} rows from CSV")

        from ingestion.normalize import prepare_books
        books = prepare_books(books_df)

        openai_client = OpenAIClient(api_key=settings.openai.API_KEY)
        print("Embedding and Storing Books into PostgreSQL")
        await embed_and_store_books(books, session_factory, openai_client)
        print("Books embedded and stored successfully")
    finally:
        if openai_client:
            await openai_client.close()
        if async_engine:
            await close_async_engine(async_engine)


def main():
    """Entry point for the PostgreSQL loader."""
    start = time.perf_counter()
    asyncio.run(load_books())
    elapsed = time.perf_counter() - start
    print(f"Ingestion finished in {elapsed:.2f} seconds")


if __name__ == "__main__":
    main()
