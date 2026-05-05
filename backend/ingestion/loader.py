import os
import asyncio
import pandas as pd

from tqdm import tqdm

from app.db import postgres
from app.db.models import BookModel
from app.clients.openai_client import OpenAIClient
from app.config import settings
import logging
logger = logging.getLogger(__name__)


# Columns we insert from `book_chunk` (embedding is inserted separately).
# We exclude `embedding` and `is_children` because the loader currently doesn't
# populate them (schema default for `is_children` will apply).
BOOK_INSERT_COLUMNS = [
    c.name
    for c in BookModel.__table__.columns
    if c.name not in ("embedding", "is_children")
]
BOOK_INSERT_COLUMNS_SQL = ", ".join(BOOK_INSERT_COLUMNS)


def clean_numeric_value(value):
    """Clean and convert numeric values, return None if invalid."""
    if pd.isna(value) or value == "" or value == "nan":
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def batchify(iterable, batch_size):
    """Split an iterable into batches of specified size."""
    for i in range(0, len(iterable), batch_size):
        yield iterable[i : i + batch_size]


# Book storage operations
async def store_books_batch(conn, books_batch):
    """Store a batch of books in PostgreSQL."""
    # Prepare the INSERT statement once per call.
    # Placeholders are $1..$N (asyncpg positional parameters).
    n = len(BOOK_INSERT_COLUMNS)
    placeholders = ", ".join([f"${i}" for i in range(1, n + 2)])  # +1 for embedding
    insert_query = f"""
        INSERT INTO books ({BOOK_INSERT_COLUMNS_SQL}, embedding)
        VALUES ({placeholders})
        ON CONFLICT (isbn13) DO NOTHING
    """

    for book in books_batch:
        values = [book[col] for col in BOOK_INSERT_COLUMNS] + [book["embedding"]]
        await conn.execute(insert_query, *values)


# Book loading and data preparation
async def load_books_from_csv(csv_path="data/books.csv", limit=None):
    """Load books from CSV/Parquet file and prepare them for embedding."""
    print(f"\nLoading books from {csv_path}")

    try:
        # Handle both CSV and Parquet files
        if csv_path.endswith(".parquet"):
            df = pd.read_parquet(csv_path)
        else:
            df = pd.read_csv(csv_path)

        print(f"Loaded {len(df)} books from {csv_path}")

        # Limit the number of books if specified
        if limit:
            df = df.head(limit)
            print(f"Limited to first {limit} books")
        else:
            print(f"Loading all {len(df)} books")

        # Create book chunks for embedding
        books = []
        book_stats = []

        print("\nPreparing books for embedding")
        # TODO: use Models.py to prepare the books
        # with defaults values for the missing columns
        for idx, row in df.iterrows():
            if pd.notna(row["title"]) and pd.notna(row["description"]):
                emotion_cols = [
                    "anger",
                    "disgust",
                    "fear",
                    "joy",
                    "sadness",
                    "surprise",
                    "neutral",
                ]
                emotions = {
                    col: clean_numeric_value(row.get(col)) or 0.0
                    for col in emotion_cols
                }
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
                    "large_thumbnail": str(row.get("large_thumbnail", "")),
                    "title_and_subtiles": str(row.get("title_and_subtiles", "")),
                    **emotions,
                }
                books.append(book_chunk)

                # Collect statistics (similar to Redis version)
                book_stat = {
                    "title": row["title"],
                    "authors": row.get("authors", ""),
                    "num_pages": row.get("num_pages", ""),
                    "description": (
                        row["description"][:200] + "..."
                        if len(str(row["description"])) > 200
                        else row["description"]
                    ),
                    "categories": row.get("categories", ""),
                    "published_year": row.get("published_year", ""),
                    "average_rating": row.get("average_rating", ""),
                    "isbn13": row.get("isbn13", ""),
                }
                book_stats.append(book_stat)

        # Save statistics to file
        stats_df = pd.DataFrame(book_stats)
        stats_file = "data/loaded_books_stats.csv"
        stats_df.to_csv(stats_file, index=False)

        print(f"Prepared {len(books)} book chunks for embedding")
        return books

    except Exception as e:
        print(f"Error loading books from CSV: {e}")
        return []


async def embed_and_store_books(books, pool, batch_size=10):
    """Create embeddings and store books in PostgreSQL using connection pool."""

    if not books:
        print("No books to embed")
        return

    # Initialize OpenAI client
    openai_client = OpenAIClient(api_key=settings.openai.API_KEY)

    try:
        print(f"\nEmbedding and storing {len(books)} books in batches of {batch_size}")

        total_embedded = 0
        batch_count = 0

        # Initialize progress bar (similar to Redis version)
        with tqdm(total=len(books), desc="Embedding books", unit="book") as pbar:
            for batch in batchify(books, batch_size):
                batch_count += 1

                try:
                    # Process batch
                    embedded_batch = []
                    for book in batch:
                        try:
                            # Build combined text for embedding here
                            combined_text = f"{book['title']}\n\n{book['description']}"

                            # Get embedding for the combined title + description text
                            embedding = await openai_client.get_embedding(combined_text)
                            if embedding:
                                book["embedding"] = embedding
                                embedded_batch.append(book)
                                total_embedded += 1
                            pbar.update(1)
                        except Exception as e:
                            print(f"\nError embedding book {book['title']}: {e}")
                            pbar.update(1)
                            continue

                    # Store batch in PostgreSQL using pool connection
                    if embedded_batch:
                        async with pool.acquire() as conn:
                            await store_books_batch(conn, embedded_batch)
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

        print(
            f"\n✅ Successfully embedded and stored {total_embedded}/{len(books)} books"
        )

    except Exception as e:
        print(f"Error during book embedding and storage: {e}")
        raise
    finally:
        # Close clients (pool is owned by the caller)
        await openai_client.close()


async def load_books(*, reset: bool = True):
    """Main function to load books from CSV/Parquet into PostgreSQL."""
    pool = None
    try:
        pool = await postgres.init_postgres()
        if not pool:
            raise RuntimeError("Failed to initialize PostgreSQL connection pool")

        if reset:
            # Matches the old loader behavior (DROP/CREATE before full load).
            await postgres.reset_books_table(pool)
        else:
            await postgres.ensure_db_schema(pool)

        # Load books from CSV/Parquet
        csv_path = "data/books.parquet"  # Match the Redis version
        if not os.path.exists(csv_path):
            csv_path = "data/books.csv"  # Fallback to CSV
            if not os.path.exists(csv_path):
                print("Error: Neither data/books.parquet nor data/books.csv found")
                return

        books = await load_books_from_csv(csv_path, limit=None)  # Load all books

        if books:
            await embed_and_store_books(books, pool, batch_size=10)
            print("\nPostgreSQL book database loaded successfully!")
            print('Run "poetry run get-loader-stats" to view loading statistics.')
        else:
            print("No books were loaded from the CSV file")

    except Exception as e:
        print(f"Error during book loading: {e}")
        raise
    finally:
        if pool:
            await postgres.close_postgres(pool)


def main():
    """Entry point for the PostgreSQL loader."""
    asyncio.run(load_books())


if __name__ == "__main__":
    main()
