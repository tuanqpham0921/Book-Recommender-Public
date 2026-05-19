"""CLI entrypoint: load books from CSV and backfill embeddings."""
import asyncio
import time
from pathlib import Path

from clients.openai_client import OpenAIClient
from config import (
    DatabaseConstants,
    FilesLocationConstants,
    IngestionConstants,
    settings,
)
from db import (
    bootstrap_schema,
    close_async_engine,
    get_async_engine,
    get_session_factory,
    is_ready,
)
from db.schema import BookModel
from ingestion.embeddings import embed_missing_books
from ingestion.store import store_books


async def load_books() -> None:
    """Load books from CSV into PostgreSQL and embed any missing vectors."""
    async_engine = None
    openai_client = None
    schema = DatabaseConstants.SCHEMA
    table = BookModel.__tablename__
    csv_path = Path(FilesLocationConstants.DATA_DIR) / FilesLocationConstants.CSV_FILE
    print(f"Running ingestion for schema: {schema} and table: {table}")
    # try:
    async_engine = get_async_engine(settings.sqlalchemy)
    session_factory = get_session_factory(async_engine)

    await bootstrap_schema(session_factory)

    ready_report = await is_ready(
        session_factory,
        schema=schema,
        table=table,
        min_rows=IngestionConstants.APPROXIMATE_LOAD_LIMIT,
    )
    ready_report.log()
    # TODO: check embedding coverage and skip embed when already done
    if not ready_report.ok:
        print("Storing Books into PostgreSQL")
        await store_books(session_factory, csv_path)

    print("Embedding missing books")
    openai_client = OpenAIClient(settings.openai)
    await embed_missing_books(session_factory, openai_client)

    # except Exception as e:
    #     raise ValueError(f"Error ingesting books: {e}") from e
    # finally:
    #     if async_engine:
    #         await close_async_engine(async_engine)
    #     if openai_client:
    #         await openai_client.close()


def main() -> None:
    """Entry point for the ingestion pipeline."""
    start = time.perf_counter()
    asyncio.run(load_books())
    elapsed = time.perf_counter() - start
    print(f"Ingestion finished in {elapsed:.2f} seconds")


if __name__ == "__main__":
    main()
