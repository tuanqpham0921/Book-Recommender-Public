import asyncio
import time
from pathlib import Path

import pandas as pd
from tqdm import tqdm

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
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert


def _embedding_text(book: dict) -> str:
    return f"{book['title']}\n\n{book['description']}"


def _count_csv_data_rows(csv_path: Path) -> int:
    """Count data rows in a CSV (excludes header). Used for tqdm totals."""
    with csv_path.open("rb") as f:
        return max(sum(1 for _ in f) - 1, 0)

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
    """Store a batch of books into the database."""
    if not batch:
        return 0
    
    table = BookModel.__table__
    stmt = insert(table).values(batch)
    update_columns = {
        column.name: stmt.excluded[column.name]
        for column in table.columns
        if column.name not in ("isbn13", "embedding")
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

async def get_missing_books(
    session_factory: async_sessionmaker[AsyncSession],
) -> list[dict]:
    """Books that exist in the DB but have no embedding yet."""
    stmt = (
        select(
            BookModel.isbn13,
            BookModel.title,
            BookModel.description,
        )
        .where(BookModel.embedding.is_(None))
        .where(BookModel.description.is_not(None))
    )
    async with session_factory() as session:
        result = await session.execute(stmt)
        return [dict(row) for row in result.mappings()]


async def update_book_embedding(
    book: dict,
    openai_client: OpenAIClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Compute an embedding and persist only the embedding column."""
    embedding = await openai_client.get_embedding(_embedding_text(book))
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
    missing_books = await get_missing_books(session_factory)
    if not missing_books:
        return 0

    for book in tqdm(
        missing_books,
        desc="Embedding books",
        unit="book",
        total=len(missing_books),
    ):
        await update_book_embedding(book, openai_client, session_factory)

    print(f"✅ Embedded {len(missing_books)} books")
    return len(missing_books)


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
        async_engine = get_async_engine(settings.sqlalchemy)
        session_factory = get_session_factory(async_engine)
        
        # bootstrap schema
        await bootstrap_schema(session_factory)
        
        # Check if database is ready or need to skip ingestion
        ready_report = await is_ready(session_factory, 
                                      schema=schema, 
                                      table=table, 
                                      min_rows=IngestionConstants.APPROXIMATE_LOAD_LIMIT)
        ready_report.log()
        # TODO: check the embedding status and only embed if it's not done
        # (current removed for testing)
        # if ready_report.ok:
        #     print("Database is ready")
        #     return
        
        print("Storing Books into PostgreSQL")
        total_books_stored = 0
        total_books = 0
        csv_row_count = _count_csv_data_rows(csv_path)
        with tqdm(
            desc="Storing books",
            unit="book",
            total=csv_row_count or None,
        ) as store_pbar:
            for batch in iter_books_from_csv(csv_path):
                total_books += len(batch)
                total_books_stored += await store_books(batch, session_factory)
                store_pbar.update(len(batch))
        
        print(f"✅ Stored {total_books_stored} books out of {total_books}")
        print("Books stored successfully")

        openai_client = OpenAIClient(settings.openai)
        await embed_missing_books(session_factory, openai_client)

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
