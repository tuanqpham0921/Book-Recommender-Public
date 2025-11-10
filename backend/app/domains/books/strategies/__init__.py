from typing import Union

from .analyze import CompareBooks, RecommendBooks
from .retrieval import FindByIsbn13, FindByTitle, FindByTraits

from app.domains.books.types import NodeType

BOOK_STRAT_REGISTRY = {
    NodeType.COMPARE: CompareBooks,
    NodeType.RECOMMENDATION: RecommendBooks,
    NodeType.FIND_ISBN13: FindByIsbn13,
    NodeType.FIND_TITLE: FindByTitle,
    NodeType.FIND_TRAITS: FindByTraits
}

__all__ = [
    "BOOK_STRAT_REGISTRY"
]