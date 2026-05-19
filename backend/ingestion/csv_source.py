"""Read book batches from CSV for ingestion."""
from pathlib import Path

import pandas as pd

from ingestion.normalize import prepare_chunk


def count_csv_data_rows(csv_path: Path) -> int:
    """Count data rows in a CSV (excludes header). Used for tqdm totals."""
    with csv_path.open("rb") as f:
        return max(sum(1 for _ in f) - 1, 0)


def iter_books_from_csv(
    csv_path: Path, *, chunksize: int = 10, limit: int | None = None
):
    """Yield prepared book dict batches from a CSV file."""
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
