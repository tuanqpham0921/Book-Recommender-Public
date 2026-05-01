# SQLAlchemy models for books domain
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Float, Text, Boolean
from pgvector.sqlalchemy import Vector

Base = declarative_base()


class BookModel(Base):
    """SQLAlchemy model for books table."""

    __tablename__ = "books"

    # Primary key
    # id = Column(Integer, primary_key=True, index=True)

    # Book identifiers
    isbn13 = Column(String(13), primary_key=True, index=True)

    # Basic book information
    title = Column(String(500), nullable=False, index=True)
    authors = Column(String, nullable=True, index=True)
    categories = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    
    # description embedding
    embedding = Column(Vector(1024), nullable=True)
    # title_embedding = Column(Vector(1536), nullable=True)
    # combined_embedding = Column(Vector(1536), nullable=True)

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
    
    # TODO: missing embedding columns

    def __repr__(self):
        return (
            f"<BookModel(isbn13='{self.isbn13}', title='{self.title}')>"
        )

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
        }
