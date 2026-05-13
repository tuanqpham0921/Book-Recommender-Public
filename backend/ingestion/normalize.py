""" Normalize the data in the database (making it more consistent and easier to use). """
from pypinyin import lazy_pinyin
import pandas as pd
from db.schema import BookModel import BookModel


def clean_numeric_value(value):
    """Clean and convert numeric values, return None if invalid."""
    if pd.isna(value) or value == "" or value == "nan":
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def prepare_books(df: pd.DataFrame) -> list[BookModel]:
    """Prepare books for embedding and storage."""
    books = []

    print("\nPreparing books for embedding")
    for idx, row in df.iterrows():
        if pd.notna(row["title"]) and pd.notna(row["description"]):
            book_chunk = {
                "isbn13": str(row.get("isbn13", "")),
                "title": str(row["title"]),
                "authors": str(row.get("authors", "")),
                "categories": str(row.get("categories", "")),
                "genre": str(row.get("simple_categories", "")),
                "description": str(row["tagged_description"]),
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
                # "anger": clean_numeric_value(row.get("anger")) or 0.0,
                # "disgust": clean_numeric_value(row.get("disgust")) or 0.0,
                # "fear": clean_numeric_value(row.get("fear")) or 0.0,
                # "joy": clean_numeric_value(row.get("joy")) or 0.0,
                # "sadness": clean_numeric_value(row.get("sadness")) or 0.0,
                # "surprise": clean_numeric_value(row.get("surprise")) or 0.0,
                # "neutral": clean_numeric_value(row.get("neutral")) or 0.0,
            }
            # convert to BookModel
            books.append(BookModel(**book_chunk))  
    return books



# -----------------------
# ----- LEGACY CODE -----
# Helper functions for changing the author name to a more consistent format
def romanize_if_needed(name: str) -> str:
    """Romanize the name if it contains CJK Unified Ideographs."""
    import re, pykakasi
    kks = pykakasi.kakasi()
    
    if re.search(r"[\u4E00-\u9FFF]", name):
        # CJK Unified Ideographs
        converted = kks.convert(name)
        if converted:
            return " ".join([item['hepburn'].capitalize() for item in converted])
        else:
            return " ".join(lazy_pinyin(name))  
    
    return name

def normalize_author(name: str) -> str:
    """Normalize the author name."""
    import re, unicodedata
    
    name = name.strip()
    name = unicodedata.normalize("NFKC", name)
    name = re.sub(r";", " ", name).strip()

    ascii_only = re.sub(r"[^a-zA-Z0-9\s]", " ", name)
    ascii_only = re.sub(r"\s+", " ", ascii_only).strip()

    return name

    # if ascii_only:
    #     return ascii_only
    # romanized = romanize_if_needed(name)
    # if romanized:
    #     print(f"Converted '{name}' to '{romanized}'")
    
    # return romanized or name