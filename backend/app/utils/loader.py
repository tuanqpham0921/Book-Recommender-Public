import os
import asyncio
import pandas as pd

from tqdm import tqdm

from app.db import postgres
from app.clients.openai_client import OpenAIClient
from app.config import settings

BOOK_COLUMNS = """isbn13, title, authors, categories, genre, description, published_year,
                 average_rating, num_pages, ratings_count, thumbnail, large_thumbnail,
                 title_and_subtiles, anger, disgust, fear, joy, sadness, surprise, neutral"""


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
    try:
        # Prepare the INSERT statement
        insert_query = f"""
            INSERT INTO books (
                {BOOK_COLUMNS}, embedding
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, 
                     $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21)
            ON CONFLICT (isbn13) DO NOTHING
        """

        # Insert each book in the batch
        for book in books_batch:
            await conn.execute(
                insert_query,
                book["isbn13"],
                book["title"],
                book["authors"],
                book["categories"],
                book["genre"],
                book["description"],
                book["published_year"],
                book["average_rating"],
                book["num_pages"],
                book["ratings_count"],
                book["thumbnail"],
                book["large_thumbnail"],
                book["title_and_subtiles"],
                book["anger"],
                book["disgust"],
                book["fear"],
                book["joy"],
                book["sadness"],
                book["surprise"],
                book["neutral"],
                book["embedding"],
            )

    except Exception as e:
        print(f"Error storing books batch: {e}")
        raise


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
                    "large_thumbnail": str(row.get("large_thumbnail", "")),
                    "title_and_subtiles": str(row.get("title_and_subtiles", "")),
                    "anger": clean_numeric_value(row.get("anger")) or 0.0,
                    "disgust": clean_numeric_value(row.get("disgust")) or 0.0,
                    "fear": clean_numeric_value(row.get("fear")) or 0.0,
                    "joy": clean_numeric_value(row.get("joy")) or 0.0,
                    "sadness": clean_numeric_value(row.get("sadness")) or 0.0,
                    "surprise": clean_numeric_value(row.get("surprise")) or 0.0,
                    "neutral": clean_numeric_value(row.get("neutral")) or 0.0,
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


async def embed_and_store_books(books, batch_size=10):
    """Create embeddings and store books in PostgreSQL using connection pool."""

    if not books:
        print("No books to embed")
        return

    # Initialize OpenAI client
    openai_client = OpenAIClient(api_key=settings.openai.API_KEY)

    # Ensure PostgreSQL pool is initialized
    pool = await postgres.init_postgres()
    if not pool:
        raise RuntimeError("Failed to initialize PostgreSQL connection pool")

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
        # Close clients
        await openai_client.close()
        await postgres.close_postgres(pool)


async def load_books():
    """Main function to load books from CSV into PostgreSQL."""
    try:
        # Initialize PostgreSQL connection pool
        pool = await postgres.init_postgres()
        if not pool:
            raise RuntimeError("Failed to initialize PostgreSQL connection pool")

        # Setup PostgreSQL database
        await postgres.setup_postgres_db(pool)

        # Load books from CSV/Parquet
        csv_path = "data/books.parquet"  # Match the Redis version
        if not os.path.exists(csv_path):
            csv_path = "data/books.csv"  # Fallback to CSV
            if not os.path.exists(csv_path):
                print(f"Error: Neither data/books.parquet nor data/books.csv found")
                return

        books = await postgres.load_books_from_csv(
            csv_path, limit=None
        )  # Load all books

        if books:
            # Embed and store books in PostgreSQL
            await embed_and_store_books(books, batch_size=10)

            print("\nPostgreSQL book database loaded successfully!")
            print('Run "poetry run get-loader-stats" to view loading statistics.')
        else:
            print("No books were loaded from the CSV file")

    except Exception as e:
        print(f"Error during book loading: {e}")
        raise
    finally:
        # Close the connection pool when done
        await postgres.close_postgres(pool)


def main():
    """Entry point for the PostgreSQL loader."""
    asyncio.run(load_books())


if __name__ == "__main__":
    main()
