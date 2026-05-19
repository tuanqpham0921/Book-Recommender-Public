"""Normalize CSV rows into book records for ingestion."""
import pandas as pd

from db.schema import BookModel


def normalize_field(value, kind: type = str) -> str | int | float | None:
    """Normalize a CSV cell to the requested Python type."""
    if kind is str:
        if pd.isna(value) or value == "":
            return ""
        return str(value)

    if pd.isna(value) or value == "" or (isinstance(value, str) and value == "nan"):
        return None

    if isinstance(value, bool):
        return None

    if isinstance(value, int):
        return value if kind is int else float(value)

    if isinstance(value, float):
        return int(value) if kind is int else value

    try:
        number = float(value)
        return int(number) if kind is int else number
    except (ValueError, TypeError):
        return None


def row_to_book(row: pd.Series) -> BookModel:
    """Map a CSV row to a BookModel (column renames and numeric cleaning)."""
    return BookModel(
        isbn13=normalize_field(row.get("isbn13"), str),
        isbn10=normalize_field(row.get("isbn10"), str),
        title=normalize_field(row["title"], str),
        authors=normalize_field(row.get("authors"), str),
        categories=normalize_field(row.get("categories"), str),
        genre=normalize_field(row.get("simple_categories"), str),
        description=normalize_field(row["tagged_description"], str),
        published_year=normalize_field(row.get("published_year"), int),
        average_rating=normalize_field(row.get("average_rating"), float),
        num_pages=normalize_field(row.get("num_pages"), int),
        ratings_count=normalize_field(row.get("ratings_count"), int),
        thumbnail=normalize_field(row.get("thumbnail"), str),
        title_and_subtiles=normalize_field(row.get("title_and_subtiles"), str),
    )


def prepare_chunk(chunk: pd.DataFrame) -> list[dict]:
    """Prepare a CSV chunk as insert-ready book dicts."""
    cleaned_chunk: list[dict] = []

    for _, row in chunk.iterrows():
        if not pd.notna(row.get("title")) or not pd.notna(row.get("tagged_description")):
            continue
        try:
            book = row_to_book(row)
            cleaned_chunk.append(book.to_dict())
        except Exception as e:
            raise ValueError(f"Error preparing chunk: {e}") from e

    return cleaned_chunk
