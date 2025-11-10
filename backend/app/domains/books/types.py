from enum import Enum
from typing import Dict, List

# ---------------------------------------------------------------


class NodeType(str, Enum):
    # Retrievals
    FIND_ISBN13 = "FindByISBN13"
    FIND_TITLE = "FindByTitle"
    FIND_TRAITS = "FindByTraits"
    
    # Strategies
    COMPARE = "Compare"
    RECOMMENDATION = "Recommendation"


# ---------------------------------------------------------------
# Groupings (runtime sets, not Unions)
# ---------------------------------------------------------------

SINGLE_BOOK_RETRIEVAL = {
    NodeType.FIND_ISBN13,
    NodeType.FIND_TITLE,
}

ALL_BOOK_RETRIEVAL = SINGLE_BOOK_RETRIEVAL

# ---------------------------------------------------------------
# Dependency rules (runtime-safe)
# ---------------------------------------------------------------

DEPENDENCY_RULES: Dict[NodeType, Dict[str, List[NodeType] | List[set]] | int] = {
    NodeType.FIND_TITLE: {
        "must_depend_on": [],
        "cannot_depend_on": ["*"],
        "priority": 0
    },
    NodeType.FIND_ISBN13: {
        "must_depend_on": [],
        "cannot_depend_on": ["*"],
        "priority": 0
    },
    NodeType.RECOMMENDATION: {
        "must_depend_on": list(ALL_BOOK_RETRIEVAL),
        "cannot_depend_on": [],
        "priority": 2
    },
    # Analyze books
    NodeType.COMPARE: {
        "must_depend_on": list(ALL_BOOK_RETRIEVAL),
        "cannot_depend_on": [],
        "priority": 3
    },
}
