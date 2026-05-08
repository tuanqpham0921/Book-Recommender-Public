import os
import asyncio
import time
import pandas as pd

from tqdm import tqdm

from normalize import clean_numeric_value, prepare_books
from data.models import BookModel
from app.clients.openai_client import OpenAIClient
from config import settings

# TODO
# need to make the ingestion in the Makefile
# need to add function comments
# need to add optimizations
# need to stream the csv file? or make it better
# DETAIL:  Key (isbn13)=(9780002005883) already exists.

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

# TODO: need to make this better with the settings file
# or for testing / local development
SCHEMA = "public"  # set this to your expected schema
TABLE = "books"
CSV_FILE = "books.csv"
LOAD_LIMIT = 5000
DEVELOPMENT_DATA_PATH = "data/books.csv"

# Create async engine using your database settings

async_engine = create_async_engine(settings.postgres.sqlalchemy_url)
AsyncSessionLocal = async_sessionmaker(async_engine, class_=AsyncSession)

def batchify(iterable, batch_size):
    """Split an iterable into batches of specified size."""
    for i in range(0, len(iterable), batch_size):
        yield iterable[i : i + batch_size]

# TODO: need to add a clean function to clean the data and remove the rows that are not valid

async def table_exists():
    async with AsyncSessionLocal() as session:        
        q_exists = text("""
            select to_regclass(:fqtn) is not null as exists_;""")
        
        fqtn = f"{SCHEMA}.{TABLE}"
        result = await session.execute(q_exists, {"fqtn": fqtn})
        table_exists = bool(result.scalar())
        
        if not table_exists:
            # schema.table doesn't exist
            print(f"Table {SCHEMA}.{TABLE} not found")
            return False
        
        print(f"Table {SCHEMA}.{TABLE} found")
        # 2) Does it have > LOAD_LIMIT rows?
        # Note: identifiers (schema/table) can't be bound params, so we embed them from trusted constants.
        q_count = text(f"SELECT COUNT(*) FROM {SCHEMA}.{TABLE}")
        result = await session.execute(q_count)
        row_count = int(result.scalar() or 0)
        
        print(f"Table {SCHEMA}.{TABLE} has {row_count} rows")
        return row_count > LOAD_LIMIT
        

async def load_books_from_csv(path: str = DEVELOPMENT_DATA_PATH, limit: int | None = None):
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
        print(f"Considering only the first {limit} CSV rows (limit applies to rows, not books)")
    else:
        print(f"Loading all {len(df)} rows")
    return df



async def embed_and_store_books(books: list, batch_size: int = 10):
    if not books:
        raise ValueError("Failed to load books from CSV")
    
    batch_count = 0
    skipped_count = 0
    total_embedded = 0
    openai_client = OpenAIClient(api_key=settings.openai.API_KEY)
    
    with tqdm(total=len(books), desc="Embedding books", unit="book") as pbar:
        for batch in batchify(books, batch_size):
            batch_count += 1
            embedded_batch = []
            for book in batch:
                try:
                    combined_text = f"{book.title}\n\n{book.description}"
                    embedding = await openai_client.get_embedding(combined_text)
                    if embedding:
                        book.embedding = embedding
                        embedded_batch.append(book)
                        total_embedded += 1
                except Exception as e:
                    print(f"Error embedding in batch {batch_count}: {e}")
                finally:
                    # One update per book only—never add len(batch) on top of this,
                    # or tqdm exceeds total and looks like you passed the limit.
                    pbar.update(1)

            pbar.set_postfix(
                Batch=batch_count,
                Stored=f"{total_embedded}/{len(books)}",
            )

            if not embedded_batch:
                continue

            try:
                async with AsyncSessionLocal() as session:
                    session.add_all(embedded_batch)
                    await session.commit()
            except Exception as e:
                print(f"Error committing batch {batch_count}")
    
    print(f"Skipped {skipped_count} books")
    print(f"Successfully embedded and stored {total_embedded}/{len(books)} books")
    await openai_client.close()
    return

async def load_books():
    """Main function to load books from CSV/Parquet into PostgreSQL."""
    if await table_exists():
        print("Skipping loading books to table.")
        return
    
    print("Loading Books from CSV")
    df = await load_books_from_csv(limit=100)
    print(f"Loaded {len(df)} books from CSV (after title/description filter)")

    books = prepare_books(df)
    print(f"Prepared {len(books)} books for embedding and storage")
    
    print(f"Embedding and Storing Books into PostgreSQL")
    await embed_and_store_books(books)
    print("Books embedded and stored successfully")
    
    
def main():
    """Entry point for the PostgreSQL loader."""
    start = time.perf_counter()
    asyncio.run(load_books())
    elapsed = time.perf_counter() - start
    print(f"Ingestion finished in {elapsed:.2f} seconds")


if __name__ == "__main__":
    main()
