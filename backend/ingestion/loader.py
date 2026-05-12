import os
import asyncio
import time
import pandas as pd

from data.models import BookModel
from clients.openai_client import OpenAIClient
from config import settings

# TODO
# need to add function comments
# need to add optimizations
# need to stream the csv file? or make it better
# DETAIL:  Key (isbn13)=(9780002005883) already exists.

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from db import close_async_engine, get_async_engine, get_session_factory

# TODO: need to make this better with the settings file
# or for testing / local development
SCHEMA = "public"  # set this to your expected schema
TABLE = "books"
CSV_FILE = "books.csv"
LOAD_LIMIT = 5000
DEVELOPMENT_DATA_PATH = "data/books.csv"


def batchify(iterable, batch_size):
    """Split an iterable into batches of specified size."""
    for i in range(0, len(iterable), batch_size):
        yield iterable[i : i + batch_size]


async def table_exists(session_factory: async_sessionmaker[AsyncSession]):
    """Check if the table exists and has more than LOAD_LIMIT rows"""

    async with session_factory() as session:
        q_exists = text(
            """
            select to_regclass(:fqtn) is not null as exists_;"""
        )

        fqtn = f"{SCHEMA}.{TABLE}"
        result = await session.execute(q_exists, {"fqtn": fqtn})
        table_exists = bool(result.scalar())

        if not table_exists:
            # schema.table doesn't exist
            print(f"❌ Table {SCHEMA}.{TABLE} not found")
            return False

        print(f"✅ Table {SCHEMA}.{TABLE} found")
        # 2) Does it have > LOAD_LIMIT rows?
        # Note: identifiers (schema/table) can't be bound params, so we embed them from trusted constants.
        q_count = text(f"SELECT COUNT(*) FROM {SCHEMA}.{TABLE}")
        result = await session.execute(q_count)
        row_count = int(result.scalar() or 0)

        print(f"Table {SCHEMA}.{TABLE} has {row_count} rows")
        return row_count > LOAD_LIMIT


def load_books_from_csv(path: str = DEVELOPMENT_DATA_PATH, limit: int | None = None):
    """Load books from CSV.

    ``limit`` caps how many **CSV rows** are read (via ``head``), not how many
    valid books you end up with—rows missing title/description are skipped, so
    the book list can be smaller than ``limit``.
    """
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
    batch_size: int = 10,
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
        if await table_exists(session_factory):
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
