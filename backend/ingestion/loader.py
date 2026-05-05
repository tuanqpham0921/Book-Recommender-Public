import os
import asyncio
from pathlib import Path
import pandas as pd

from tqdm import tqdm

from app.db import postgres
from app.db.models import BookModel
from app.clients.openai_client import OpenAIClient
from app.config import settings
import logging
logger = logging.getLogger(__name__)

# Default data paths (override via env vars if desired).
DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
BOOKS_PARQUET_PATH = Path(os.getenv("BOOKS_PARQUET_PATH", str(DATA_DIR / "books.parquet")))
BOOKS_CSV_PATH = Path(os.getenv("BOOKS_CSV_PATH", str(DATA_DIR / "books.csv")))
LOADER_STATS_PATH = Path(
    os.getenv("LOADER_STATS_PATH", str(DATA_DIR / "loaded_books_stats.csv"))
)


# Columns we insert from `book_chunk` (embedding is inserted separately).
# We exclude `embedding` and `is_children` because the loader currently doesn't
# populate them (schema default for `is_children` will apply).
BOOK_INSERT_COLUMNS = [
    c.name
    for c in BookModel.__table__.columns
    if c.name not in ("embedding", "is_children")
]
BOOK_INSERT_COLUMNS_SQL = ", ".join(BOOK_INSERT_COLUMNS)

_MODEL_COLUMN_NAMES = {c.name for c in BookModel.__table__.columns}
_MODEL_EMOTION_COLUMNS = sorted(
    _MODEL_COLUMN_NAMES
    & {"anger", "disgust", "fear", "joy", "sadness", "surprise", "neutral"}
)

# DB column -> CSV column overrides
_CSV_TO_DB_OVERRIDES = {
    "genre": "simple_categories",
}

_INT_COLUMNS = {"published_year", "num_pages", "ratings_count"}
_FLOAT_COLUMNS = {"average_rating", *_MODEL_EMOTION_COLUMNS}


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


def _read_books_dataframe(csv_path: str) -> pd.DataFrame:
    """Load input data from CSV or parquet based on file extension."""
    path = Path(csv_path)
    suffix = path.suffix.lower()
    if suffix == ".parquet":
        return pd.read_parquet(path)
    if suffix == ".csv":
        return pd.read_csv(path)
    raise ValueError(f"Unsupported file type: {suffix}")

def resolve_books_input_path() -> Path:
    """Pick parquet if present; otherwise fall back to CSV."""
    if BOOKS_PARQUET_PATH.exists():
        return BOOKS_PARQUET_PATH
    return BOOKS_CSV_PATH


def _to_str(value) -> str:
    if pd.isna(value) or value == "nan":
        return ""
    return str(value)


def _to_int(value):
    x = clean_numeric_value(value)
    return int(x) if x is not None else None


def _to_float(value):
    return clean_numeric_value(value)


def _row_to_book_chunk(row: pd.Series) -> dict:
    """Convert a dataframe row to the dict shape expected by store_books_batch()."""
    chunk = {}

    for col in BOOK_INSERT_COLUMNS:
        csv_col = _CSV_TO_DB_OVERRIDES.get(col, col)
        value = row.get(csv_col)

        if col in _INT_COLUMNS:
            chunk[col] = _to_int(value)
        elif col in _FLOAT_COLUMNS:
            f = _to_float(value)
            chunk[col] = (f if f is not None else 0.0) if col in _MODEL_EMOTION_COLUMNS else f
        else:
            chunk[col] = _to_str(value)

    # Ensure required fields are present as strings.
    chunk["isbn13"] = _to_str(row.get("isbn13"))
    chunk["title"] = _to_str(row.get("title"))
    chunk["description"] = _to_str(row.get("description"))
    return chunk


def _row_to_book_stat(row: pd.Series) -> dict:
    description = _to_str(row.get("description"))
    return {
        "title": _to_str(row.get("title")),
        "authors": _to_str(row.get("authors")),
        "num_pages": row.get("num_pages", ""),
        "description": (description[:200] + "...") if len(description) > 200 else description,
        "categories": _to_str(row.get("categories")),
        "published_year": row.get("published_year", ""),
        "average_rating": row.get("average_rating", ""),
        "isbn13": _to_str(row.get("isbn13")),
    }


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
async def load_books_from_csv(csv_path: str | Path = None, limit=None):
    """Load books from CSV/Parquet file and prepare them for embedding."""
    csv_path = str(csv_path or BOOKS_CSV_PATH)
    print(f"\nLoading books from {csv_path}")

    try:
        df = _read_books_dataframe(csv_path)

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
        for _, row in df.iterrows():
            # Only embed when both fields exist (matches previous logic).
            if pd.notna(row.get("title")) and pd.notna(row.get("description")):
                books.append(_row_to_book_chunk(row))
                book_stats.append(_row_to_book_stat(row))

        # Save statistics to file
        stats_df = pd.DataFrame(book_stats)
        stats_df.to_csv(LOADER_STATS_PATH, index=False)

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
        input_path = resolve_books_input_path()
        if not input_path.exists():
            print(f"Error: input file not found at {input_path}")
            return

        books = await load_books_from_csv(str(input_path), limit=None)  # Load all books

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
