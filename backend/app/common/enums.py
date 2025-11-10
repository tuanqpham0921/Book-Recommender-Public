from enum import Enum

class Role(str, Enum):
    SYSTEM    = "system"
    USER      = "user"
    ASSISTANT = "assistant"
    TOOL      = "tool"

class StatusEnum(str, Enum):
    SUCCESS = "success"
    FAILED  = "failed"
    PENDING = "pending"

class ActionEnum(str, Enum):
    ADD    = "add"
    REMOVE = "remove"

# -----------------------------------------
class DomainEnum(str, Enum):
    BOOKS   = "books"
    PROJECT = "project"
    META    = "meta"     # memory, context, state/history
    UNKNOWN = "unknown"  # fallback / catch-all

class GenreEnum(str, Enum):
    FICTION    = "fiction"
    NONFICTION = "non-fiction"
    
class ToneEnum(str, Enum):
    ANGER    = "anger"
    DISGUST  = "disgust"
    FEAR     = "fear"
    JOY      = "joy"
    SADNESS  = "sadness"
    SURPRISE = "surprise"
    NEUTRAL  = "neutral"

# -----------------------------------------
class SafeNumOpEnum(str, Enum):
    GT  = ">"
    GTE = ">="
    LT  = "<"
    LTE = "<="
    
class SafeStrOpEnum(str, Enum):
    EQ    = "="
    LIKE  = "LIKE"
    ILIKE = "ILIKE"

class SafeBoolOpEnum(str, Enum):
    EQ = "="
    IS = "IS"
    IS_NOT = "IS NOT"
    
# -----------------------------------------

class MetricEnum(str, Enum):
    COUNT = "count"
    AVG   = "avg"
    SUM   = "sum"
    MIN   = "min"
    MAX   = "max"


class BookFieldEnum(str, Enum):
    ISBN13         = "isbn13"
    TITLE_COL      = "title"
    AUTHORS        = "authors"
    CATEGORIES     = "categories"
    DESCRIPTION    = "description"
    PUBLISHED_YEAR = "published_year"
    AVERAGE_RATING = "average_rating"
    RATINGS_COUNT  = "ratings_count"
    NUM_PAGES      = "num_pages"
    IS_CHILDREN    = "is_children"
    GENRE          = "genre"

class BookSimilarityBasisEnum(str, Enum):
    TONE  =  "tone"
    THEME = "theme"
    STYLE = "style"