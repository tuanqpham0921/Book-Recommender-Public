# SQLAlchemy models (shared by stores / DB layers)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Float, Text, Boolean
from pgvector.sqlalchemy import Vector

from app.config import settings

Base = declarative_base()

# TODO: this is an ORM file, we should avoid confusion with dataclasses
class BookModel(Base):
    """SQLAlchemy model for books table."""

    __tablename__ = "books"

    # Book identifiers
    isbn13 = Column(String(13), primary_key=True, index=True)

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
    ratings_count = Column(Integer, nullable=True)

    # Emotion scores (used for recommendations / analysis)
    anger = Column(Float, nullable=True, default=0.0)
    disgust = Column(Float, nullable=True, default=0.0)
    fear = Column(Float, nullable=True, default=0.0)
    joy = Column(Float, nullable=True, default=0.0)
    sadness = Column(Float, nullable=True, default=0.0)
    surprise = Column(Float, nullable=True, default=0.0)
    neutral = Column(Float, nullable=True, default=0.0)

    # Misc presentation fields
    title_and_subtiles = Column(Text, nullable=True)

    def __repr__(self):
        return f"<BookModel(isbn13='{self.isbn13}', title='{self.title}')>"

    def to_dict(self) -> dict:
        """Convert model to dictionary."""
        return {
            "isbn13": self.isbn13,
            "title": self.title,
            "authors": self.authors,
            "categories": self.categories,
            "description": self.description,
            "published_year": self.published_year,
            "num_pages": self.num_pages,
            "average_rating": self.average_rating,
            "ratings_count": self.ratings_count,
            "is_children": self.is_children,
            "genre": self.genre,
            "thumbnail": self.thumbnail,
            "title_and_subtiles": self.title_and_subtiles,
            "anger": self.anger,
            "disgust": self.disgust,
            "fear": self.fear,
            "joy": self.joy,
            "sadness": self.sadness,
            "surprise": self.surprise,
            "neutral": self.neutral,
        }
