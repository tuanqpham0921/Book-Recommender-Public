from typing import Optional, Literal
from pydantic import BaseModel, Field, ConfigDict
from app.config import BookConstraints

from app.common.enums import GenreEnum


class ExclusionBookFilter(BaseModel):
    model_config = ConfigDict(extra="forbid")
    
    book_titles: Optional[list[str]] = Field(default=None, description="Titles to exclude.")
    authors: Optional[list[str]] = Field(default=None, description="Authors to exclude.")
    categories: Optional[list[str]] = Field(default=None, description="List of categories or subgenres.")
    # keywords: Optional[list[str]] = Field(default=None, description="Keywords for semantic or fuzzy matching.")

    def model_post_init(self, __context) -> None:
        if self.book_titles:
            self.book_titles = list(set(self.book_titles))
        
        if self.authors:
            self.authors = list(set(self.authors))
        
        if self.categories:
            self.categories = list(set(self.categories))


class BooksFilter(BaseModel):
    model_config = ConfigDict(extra="forbid")

    authors: Optional[list[str]] = Field(default=None, description="Authors to include.")
    categories: Optional[list[str]] = Field(default=None, description="List of categories or subgenres.")
    keywords: Optional[list[str]] = Field(default=None, description="Keywords for semantic or fuzzy matching.")
    # fuzzy_priority: Optional[Literal["authors", "categories"]] = Field(default=None, description="Fuzzy match priority of genere or author")
    
    genre: Optional[GenreEnum] = Field(default=None, description="Main genre of the book.")
    is_children: Optional[bool] = Field(default=None, description="If True, include only child-friendly books.")
    # language: Optional[str] = Field(default=None, description="Language code (e.g., 'en').")
    # edition_type: Optional[str] = Field(default=None, description="Edition type (paperback, hardcover, ebook).")

    min_pages: Optional[int] = Field(default=None)
    max_pages: Optional[int] = Field(default=None)
    min_year: Optional[int] = Field(default=None)
    max_year: Optional[int] = Field(default=None)
    min_rating: Optional[float] = Field(default=None)
    max_rating: Optional[float] = Field(default=None)

    sort_by: Optional[Literal["rating", "page_count", "published_year"]] = None
    sort_order: Literal["asc", "desc"] = "desc"

    limit: int = Field(default=BookConstraints.default_limit)
    exclusion: Optional[ExclusionBookFilter] = None

    def model_post_init(self, __context) -> None:
        if self.authors:
            self.authors = list(set(self.authors))
        
        if self.categories:
            self.categories = list(set(self.categories))
            
        if self.keywords:
            self.keywords = list(set(self.keywords))
        
