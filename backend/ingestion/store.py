"""Persist normalized book rows to PostgreSQL."""
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import select
from db.schema import BookModel
from ingestion.csv_source import count_csv_data_rows, iter_books_from_csv


async def insert_batch(
    batch: list[dict],
    session_factory: async_sessionmaker[AsyncSession],
) -> int:
    """Upsert a batch of books (metadata only; embedding column excluded on conflict)."""
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


async def store_books(
    session_factory: async_sessionmaker[AsyncSession],
    csv_path: Path,
) -> int:
    """Load books from CSV into the database."""
    total_books_stored = 0
    total_books = 0
    csv_row_count = count_csv_data_rows(csv_path)
    print(f"🔍 Storing {csv_row_count} books")
    for batch in iter_books_from_csv(csv_path):
        total_books += len(batch)
        total_books_stored += await insert_batch(batch, session_factory)
        print(f"✅ Stored {total_books_stored} books")
        
    if total_books_stored != total_books:
        raise ValueError(f"❌ Expected to store {total_books} books, but only stored {total_books_stored} books")
    
    return total_books_stored
