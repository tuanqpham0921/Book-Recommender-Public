
class AppConfig:
    """System-level constants."""
    SESSION_PREFIX   = "session"
    REDIS_TIMEOUT    = 5.0
    POSTGRES_TIMEOUT = 10.0
    OPENAI_TIMEOUT   = 10.0
    DEFAULT_TIMEOUT  = 10.0
    
class AppPolicyConfig:
    """Operational policies for runtime behavior."""
    MAX_BOOK_RESULTS  = 20       # max number of books returned per query
    MAX_API_RETRIES   = 3        # how many times to retry a failed API call
    RETRY_BACKOFF_SEC = 2.0      # backoff delay between retries
    MAX_PARALLEL_REQUESTS  = 5   # throttle concurrent OpenAI or DB calls
    API_RATE_LIMIT_PER_MIN = 60  # requests per minute per user/session
    CACHE_TTL_SEC = 3600         # default cache expiration for recommendations


class LLMPolicyConfig:
    """Constraints and policies for LLM calls and token usage."""

    # ---- Context & generation limits ----
    MAX_CONTEXT_TOKENS    = 128_000  # model limit (e.g. GPT-4.1-mini total context window)
    MAX_GENERATION_TOKENS = 2_000    # max tokens for one assistant completion

    # ---- Conversation management ----
    USER_CONTEXT_TOKEN_LIMIT   = 20_000  # cap user chat history before summarization
    SYSTEM_CONTEXT_TOKEN_LIMIT = 4_000   # reserved for system + prompt templates
    TOOL_CONTEXT_TOKEN_LIMIT   = 2_000   # reserved for tool messages, etc.
    LAST_N_USER_MESSAGES       = 4       # always keep last N user messages in full

    # ---- Safety / fallback ----
    MAX_TOTAL_HISTORY_TOKENS = 32_000  # truncate Redis or Postgres chat history beyond this
    MIN_SUMMARIZE_THRESHOLD  = 12_000  # when to start summarizing user messages

class BookGuides:
    CLASSICAL_YEAR    = "before 1900"
    EARLY_MODERN_YEAR = "between 1900 and 1950"
    HISTORICAL_YEAR   = "between 1950 and 2000"
    MODERN_YEAR       = "between 2000 and 2015"
    RECENT_YEAR       = "after 2016 to present"   
    
    RATING_POOR        = "less than 2.0"
    RATING_BELOW_AVG   = "between 2.0 and 3.0"
    RATING_AVERAGE     = "between 3.0 and 4.0"
    RATING_GOOD        = "between 4.0 and 4.5"
    RATING_EXCELLENT   = "more than 4.5"
    
    SHORT_BOOK       = "less than 150 pages"
    MEDIUM_BOOK      = "between 150 and 300 pages" 
    LONG_BOOK        = "betwen 300 and 500 pages"
    VERY_LONG_BOOK   = "more than 500 pages"
    
    def __str__(self):
        """Return string representation of all constraints."""
        result = "BookConstraints:\n"
        
        # Get all class attributes that are constants (uppercase or constraint names)
        constraints = {
            name: value for name, value in self.__class__.__dict__.items()
            if not name.startswith('_') and not callable(value)
        }
        
        for attr_name, attr_value in constraints.items():
            result += f"  {attr_name} = {attr_value}\n"
            
        return result

class BookConstraints:
    """Domain constraints for book data."""
    MIN_PAGE_COUNT = 4
    MAX_PAGE_COUNT = 3342
    
    MIN_RATING = 0.0
    MAX_RATING = 5.0
    
    MIN_PUBLISHED_YEAR = 1876
    MAX_PUBLISHED_YEAR = 2019

    MIN_LIMIT = 1
    MAX_LIMIT = 5
    default_limit = 3

    def __str__(self):
        """Return string representation of all constraints."""
        result = "BookConstraints:\n"
        
        # Get all class attributes that are constants (uppercase or constraint names)
        constraints = {
            name: value for name, value in self.__class__.__dict__.items()
            if not name.startswith('_') and not callable(value)
        }
        
        for attr_name, attr_value in constraints.items():
            result += f"  {attr_name} = {attr_value}\n"
            
        return result