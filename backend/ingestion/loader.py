import os
import asyncio
import time
import pandas as pd

from db.schema import BookModel
from clients.openai_client import OpenAIClient
from config import settings
from config.bootstrap import IngestionConstants

from db import (
    bootstrap_schema,
    close_async_engine,
    get_async_engine,
    get_session_factory,
    is_ready,
)
from config.bootstrap import DatabaseConstants
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

def batchify(iterable, batch_size):
    """Split an iterable into batches of specified size."""
    for i in range(0, len(iterable), batch_size):
        yield iterable[i : i + batch_size]

def load_books_from_csv(path: str = settings.app.DATA_DIR, 
                        csv_file: str = IngestionConstants.CSV_FILE,
                        limit: int = None):
    """Load books from CSV.

    ``limit`` caps how many **CSV rows** are read (via ``head``), not how many
    valid books you end up with—rows missing title/description are skipped, so
    the book list can be smaller than ``limit``.
    """
    path = os.path.join(path, csv_file)
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
    schema=DatabaseConstants.SCHEMA
    table=BookModel.__tablename__
    
    print(f"Running ingestion for schema: {schema} and table: {table}")
    try:
        # Get database connection
        async_engine = get_async_engine()
        session_factory = get_session_factory(async_engine)
        
        # bootstrap schema
        await bootstrap_schema(session_factory)
        
        # Check if database is ready or need to skip ingestion
        ready_report = await is_ready(session_factory, 
                                      schema=schema, 
                                      table=table, 
                                      min_rows=IngestionConstants.APPROXIMATE_LOAD_LIMIT)
        if ready_report.ok:
            print(f"Database already has enough rows; skipping ingestion for schema: {schema} and table: {table}")
            return
        else:
            failed_checks = [check for check in ready_report.checks if not check.ok]
            # This should only failed if there's not enough rows in the table
            # But in the future, as we have more extensions, we might need to add more checks
            print(f"Failed checks: {failed_checks}, continuing with ingestion")
            
        # Load books from CSV
        print("Loading Books from CSV")
        books_df = load_books_from_csv()
        print(f"Loaded {len(books_df)} rows from CSV")

        # Normalize books
        from ingestion.normalize import prepare_books
        books = prepare_books(books_df)

        # Embed and store books
        openai_client = OpenAIClient(api_key=settings.openai.API_KEY)
        print("Embedding and Storing Books into PostgreSQL")
        
        await embed_and_store_books(books, session_factory, openai_client)
        print("Books embedded and stored successfully")
        
    except Exception as e:
        raise ValueError(f"Error ingesting books: {e}")
    finally:
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
