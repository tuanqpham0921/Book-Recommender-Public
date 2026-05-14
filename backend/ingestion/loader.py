import asyncio
import time
from pathlib import Path

import pandas as pd

from db.schema import BookModel
from clients.openai_client import OpenAIClient
from config import DatabaseConstants, FilesLocationConstants, IngestionConstants, settings

from db import (
    bootstrap_schema,
    close_async_engine,
    get_async_engine,
    get_session_factory,
    is_ready,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.dialects.postgresql import insert

async def embed_batch(batch: list[dict], openai_client: OpenAIClient) -> list[dict]:
    """Embed a batch of books using OpenAI."""
    for book in batch:
        book.embedding = await openai_client.get_embedding(
            book.title + "\n\n" + book.description
        )

    return batch

def iter_books_from_csv(csv_path: Path, *, chunksize: int = 10, limit: int | None = None):
    from ingestion.normalize import prepare_chunk
    
    rows_seen = 0
    for chunk in pd.read_csv(csv_path, chunksize=chunksize):
        cleaned_chunk = prepare_chunk(chunk)
        if limit is not None and len(cleaned_chunk) + rows_seen > limit:
            remaining = limit - rows_seen 
            if remaining <= 0:
                break
            cleaned_chunk = cleaned_chunk[:remaining]
            
        rows_seen += len(cleaned_chunk)
        
        yield cleaned_chunk  
        
        if limit is not None and rows_seen >= limit:
            break
        

async def store_books(
    batch: list[dict],
    session_factory: async_sessionmaker[AsyncSession],
) -> int:
    if not batch:
        return 0
    table = BookModel.__table__
    stmt = insert(table).values(batch)
    update_columns = {
        column.name: stmt.excluded[column.name]
        for column in table.columns
        if column.name != "isbn13"
    }
    stmt = stmt.on_conflict_do_update(
        index_elements=["isbn13"],
        set_=update_columns,
    )
    try:
        async with session_factory() as session:
            result = await session.execute(stmt)
            await session.commit()
        return result.rowcount or 0
    except Exception as e:
        print(f"❌ Error committing batch: {e}")
        return 0


async def load_books():
    """Main function to load books from CSV/Parquet into PostgreSQL."""
    async_engine = None
    openai_client = None
    schema=DatabaseConstants.SCHEMA
    table=BookModel.__tablename__
    csv_path = Path(FilesLocationConstants.DATA_DIR) / FilesLocationConstants.CSV_FILE
    
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
        ready_report.log()
        
        print("Storing Books into PostgreSQL")
        total_books_stored = 0
        total_books = 0
        # Store books
        for batch in iter_books_from_csv(csv_path):
            total_books += len(batch)
            total_books_stored += await store_books(batch, session_factory)
        
        print(f"✅ Stored {total_books_stored} books out of {total_books}")
        print("Books stored successfully")
        
    except Exception as e:
        raise ValueError(f"Error ingesting books: {e}")
    finally:
        if async_engine:
            await close_async_engine(async_engine)
        if openai_client:
            await openai_client.close()

def main():
    """Entry point for the PostgreSQL loader."""
    start = time.perf_counter()
    asyncio.run(load_books())
    elapsed = time.perf_counter() - start
    print(f"Ingestion finished in {elapsed:.2f} seconds")


if __name__ == "__main__":
    main()
