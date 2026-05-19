# SQLAlchemy models (shared by stores / DB layers)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Float, Text, Boolean
from pgvector.sqlalchemy import Vector

from config import settings

Base = declarative_base()

# TODO: this is an ORM file, we should avoid confusion with dataclasses
class BookModel(Base):
    """SQLAlchemy model for books table."""

    __tablename__ = "books"

    # Book identifiers
    isbn13 = Column(String(13), primary_key=True, index=True)
    isbn10 = Column(String(10), nullable=True, index=True)

    # Basic book information
    title = Column(String(500), nullable=False, index=True)
    authors = Column(String, nullable=True, index=True)
    categories = Column(String, nullable=True)
    description = Column(Text, nullable=True)

    # description embedding
    embedding = Column(Vector(settings.openai.EMBEDDING_DIMENSIONS), nullable=True)

    # Publication details
    published_year = Column(Integer, nullable=True, index=True)

    # Physical properties
    num_pages = Column(Integer, nullable=True)

    # Ratings and reviews
    average_rating = Column(Float, nullable=True, index=True)

    # Content flags
    is_children = Column(Boolean, nullable=True, default=False)

    # Search and recommendation fields
    genre = Column(String(100), nullable=True, index=True)

    thumbnail = Column(String, nullable=True)
    # large_thumbnail = Column(String, nullable=True)

    ratings_count = Column(Integer, nullable=True)

    # Misc presentation fields
    title_and_subtiles = Column(Text, nullable=True)

    def __repr__(self):
        return f"<BookModel(isbn13='{self.isbn13}', title='{self.title}')>"

    def to_dict(self, *, include_embedding: bool = False) -> dict:
        """Convert model to dictionary (table columns only)."""
        columns = BookModel.__table__.columns
        if not include_embedding:
            columns = [c for c in columns if c.name != "embedding"]
        return {column.name: getattr(self, column.name) for column in columns}
