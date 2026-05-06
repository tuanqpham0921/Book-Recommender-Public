import os
import asyncio
from pathlib import Path
import pandas as pd

from tqdm import tqdm

from app.db import postgres
from app.db.models import BookModel
from app.clients.openai_client import OpenAIClient
from app.config import settings

# TODO: need to use the logging config from the app 
# (with update for ingestion config)
# but for now, we will use the basic logging config
import logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.config.settings import settings

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
    return df

async def embed_and_store_books(books: pd.DataFrame, batch_size: int = 10):
    if not books:
        raise ValueError("Failed to load books from CSV")
    
    batch_count = 0
    skipped_count = 0
    total_embedded = 0
    openai_client = OpenAIClient(api_key=settings.openai.API_KEY)
    
    with tqdm(total=len(books), desc="Embedding books", unit="book") as pbar:
        for batch in batchify(books, batch_size):
            batch_count += 1
            try:
                embedded_batch = []
                for book in batch:
                    if not book['title'] or not book['description']:
                        skipped_count += 1
                        continue
                    
                    combined_text = f"{book['title']}\n\n{book['description']}"
                    embedding = await openai_client.get_embedding(combined_text)
                    if embedding:
                        book["embedding"] = embedding
                        embedded_batch.append(book)
                        total_embedded += 1
                    pbar.update(1)
                    
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
