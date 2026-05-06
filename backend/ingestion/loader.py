import os
import asyncio
from pathlib import Path
import pandas as pd

from tqdm import tqdm

from app.db import postgres
from app.db.models import BookModel
from app.clients.openai_client import OpenAIClient
from app.config import settings

# TODO
# need to make the ingestion in the Makefile
# need to add function comments
# need to add timer and optimizations
# need to stream the csv file? or make it better
# I think the emotion stats can be better (null)?

# TODO: need to use the logging config from the app 
# (with update for ingestion config)
# but for now, we will use the basic logging config
import logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.config.settings import settings

# TODO: need to make this better with the settings file
# or for testing / local development
SCHEMA = "public"  # set this to your expected schema
TABLE = "books"
CSV_FILE = "books.csv"
LOAD_LIMIT = 5000
DEVELOPMENT_DATA_PATH = "data/books.csv"
INIT_SQL_FILE = "app/db/init.sql"

# Create async engine using your database settings

async_engine = create_async_engine(settings.postgres.sqlalchemy_url)
AsyncSessionLocal = async_sessionmaker(async_engine, class_=AsyncSession)

def batchify(iterable, batch_size):
    """Split an iterable into batches of specified size."""
    for i in range(0, len(iterable), batch_size):
        yield iterable[i : i + batch_size]
        

async def run_init_sql() -> None:
    # TODO: need to make this better with the init sql file (from docker compose?)
    # then we don't need to check if the table exists
    # and we can run add functionality 
    raw = Path(INIT_SQL_FILE).read_text(encoding="utf-8")
    lines = [ln for ln in raw.splitlines() if ln.strip() and not ln.strip().startswith("--")]
    blob = "\n".join(lines)
    statements = [s.strip() for s in blob.split(";") if s.strip()]
    async with async_engine.begin() as conn:
        for stmt in statements:
            await conn.execute(text(stmt))

# TODO: need to add a clean function to clean the data and remove the rows that are not valid
def clean_numeric_value(value):
    """Clean and convert numeric values, return None if invalid."""
    if pd.isna(value) or value == "" or value == "nan":
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None

async def table_exists():
    # TODO: need to make this only add the missing rows to the table
    # ISBN13 is primary key so we can use that. try to have the 5000 books for dev
    async with AsyncSessionLocal() as session:        
        q_exists = text("""
            select to_regclass(:fqtn) is not null as exists_;""")
        
        fqtn = f"{SCHEMA}.{TABLE}"
        result = await session.execute(q_exists, {"fqtn": fqtn})
        table_exists = bool(result.scalar())
        
        if not table_exists:
            # schema.table doesn't exist
            logger.info(f"Table {SCHEMA}.{TABLE} not found")
            return False
        
        logger.info(f"Table {SCHEMA}.{TABLE} found")
        # 2) Does it have > LOAD_LIMIT rows?
        # Note: identifiers (schema/table) can't be bound params, so we embed them from trusted constants.
        q_count = text(f"SELECT COUNT(*) FROM {SCHEMA}.{TABLE}")
        result = await session.execute(q_count)
        row_count = int(result.scalar() or 0)
        
        # TODO: Uncomment this when we want to drop the table if it has less than LOAD_LIMIT rows
        # might not be good idea to drop the table if it has less than LOAD_LIMIT rows
        # logger.info(f"Table {SCHEMA}.{TABLE} has less than {LOAD_LIMIT} rows")
        # await session.execute(text(f"DROP TABLE IF EXISTS {SCHEMA}.{TABLE} CASCADE"))
        
        logger.info(f"Table {SCHEMA}.{TABLE} has {row_count} rows")
        return row_count > LOAD_LIMIT
        

async def load_books_from_csv(path: str = DEVELOPMENT_DATA_PATH, limit: int = None):
    if not os.path.exists(path):
        raise FileNotFoundError(f"File {path} does not exist")
    
    df = pd.read_csv(path)
    if limit:
        df = df.head(limit)
        logger.info(f"Limited to first {limit} rows")
    else:
        logger.info(f"Loading all {len(df)} rows")
    
    # Create book chunks for embedding
    # TODO: need to add a function to create the book chunks
    books = []

    # TODO: need to this better with the book model
    logger.info("\nPreparing books for embedding")
    for idx, row in df.iterrows():
        if pd.notna(row["title"]) and pd.notna(row["description"]):
            book_chunk = {
                "isbn13": str(row.get("isbn13", "")),
                "title": str(row["title"]),
                "authors": str(row.get("authors", "")),
                "categories": str(row.get("categories", "")),
                "genre": str(row.get("simple_categories", "")),
                "description": str(row["description"]),
                "published_year": (
                    int(clean_numeric_value(row.get("published_year")))
                    if clean_numeric_value(row.get("published_year"))
                    else None
                ),
                "average_rating": clean_numeric_value(row.get("average_rating")),
                "num_pages": (
                    int(clean_numeric_value(row.get("num_pages")))
                    if clean_numeric_value(row.get("num_pages"))
                    else None
                ),
                "ratings_count": (
                    int(clean_numeric_value(row.get("ratings_count")))
                    if clean_numeric_value(row.get("ratings_count"))
                    else None
                ),
                "thumbnail": str(row.get("thumbnail", "")),
                "title_and_subtiles": str(row.get("title_and_subtiles", "")),
                "anger": clean_numeric_value(row.get("anger")) or 0.0,
                "disgust": clean_numeric_value(row.get("disgust")) or 0.0,
                "fear": clean_numeric_value(row.get("fear")) or 0.0,
                "joy": clean_numeric_value(row.get("joy")) or 0.0,
                "sadness": clean_numeric_value(row.get("sadness")) or 0.0,
                "surprise": clean_numeric_value(row.get("surprise")) or 0.0,
                "neutral": clean_numeric_value(row.get("neutral")) or 0.0,
            }
            # convert to BookModel
            books.append(BookModel(**book_chunk))  
    
    return books

async def embed_and_store_books(books: list, batch_size: int = 10):
    if not books:
        raise ValueError("Failed to load books from CSV")
    
    batch_count = 0
    skipped_count = 0
    total_embedded = 0
    openai_client = OpenAIClient(api_key=settings.openai.API_KEY)
    
    # TODO: need to make this async
    with tqdm(total=len(books), desc="Embedding books", unit="book") as pbar:
        for batch in batchify(books, batch_size):
            batch_count += 1
            try:
                embedded_batch = []
                for book in batch:
                    
                    combined_text = f"{book.title}\n\n{book.description}"
                    embedding = await openai_client.get_embedding(combined_text)
                    if embedding:
                        book.embedding = embedding
                        embedded_batch.append(book)
                        total_embedded += 1
                    pbar.update(1)
                
                # TODO: need to make this better, transaction(?)
                if embedded_batch:
                    async with AsyncSessionLocal() as session:
                        session.add_all(embedded_batch)
                        await session.commit()
                        
                    pbar.set_postfix(
                        {
                            "Batch": f"{batch_count}",
                            "Stored": f"{total_embedded}/{len(books)}",
                        }
                    )
                    
            except Exception as e:
                print(f"\nError processing batch {batch_count}: {e}")
                # Update progress bar for failed books in this batch
                pbar.update(len(batch))
                continue
    
    logger.info(f"Skipped {skipped_count} books")
    logger.info(f"Successfully embedded and stored {total_embedded}/{len(books)} books")
    await openai_client.close()
    return

async def load_books():
    """Main function to load books from CSV/Parquet into PostgreSQL."""
    if await table_exists():
        logger.info("Skipping loading books to table.")
        return
    
    logger.info("Running init SQL")
    await run_init_sql()
    logger.info("Init SQL completed")
    
    logger.info("Loading Books from CSV")
    df = await load_books_from_csv()
    logger.info(f"Loaded {len(df)} rows from CSV")
    
    logger.info("Embedding and Storing Books into PostgreSQL")
    await embed_and_store_books(df)
    logger.info("Books embedded and stored successfully")
    
    
def main():
    """Entry point for the PostgreSQL loader."""
    asyncio.run(load_books())


if __name__ == "__main__":
    main()
