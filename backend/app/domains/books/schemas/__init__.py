from typing import Union

from .filter_schemas import BooksFilter

from .request_schemas import (
    CompareStrategy,
    RecommendationStrategy,
    FindByTitleRetrieval,
    FindByISBN13Retrieval,
    FindByTraitsRetrieval
)

AnalyzeTask = Union[
    CompareStrategy,
    RecommendationStrategy,
]

RetrievalTask = Union[
    FindByTitleRetrieval,
    FindByISBN13Retrieval,
    FindByTraitsRetrieval
]

ClassificationStrategy = Union[
    RetrievalTask,
    AnalyzeTask, 
]

__all__ = [
    "BooksFilter",
    "AnalyzeTask",
    "RetrievalTask",
    "ClassificationStrategy",
    "CompareStrategy",
    "RecommendationStrategy",
    "FindByTitleRetrieval",
    "FindByISBN13Retrieval",
    "FindByTraitsRetrieval",
]