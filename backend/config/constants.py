from pathlib import Path
""" Centralized constants for the application.
Makefile and docker compose will need to update (manually) if these are changed.
"""

PROJECT_ROOT = Path(__file__).resolve().parent.parent

class AppConfig:
    """System-level constants."""
    SESSION_PREFIX   = "session"
    DATABASE_TIMEOUT = 10.0  # SQLAlchemy engine init / connectivity
    OPENAI_TIMEOUT   = 10.0
    DEFAULT_TIMEOUT  = 10.0



class DatabaseConstants:
    """Database constants."""
    SCHEMA = "public"

class FilesLocationConstants:
    """Repository paths resolved from the backend package root."""

    PROJECT_ROOT = PROJECT_ROOT
    DATA_DIR = PROJECT_ROOT / "data"
    CSV_FILE = "books.csv"
    
    ENV_FILE = PROJECT_ROOT / "config" / ".env"
    
    EXAMPLE_PROMPT_DIR = DATA_DIR / "prompt_example"
    PROMPTS_DIR = PROJECT_ROOT / "app" / "prompts"
    EXPORT_DIR = PROJECT_ROOT / "logs"
    BACKUP_DIR = DATA_DIR / "backup"
    SCHEMA_DIR = PROJECT_ROOT / "db" / "schema"
    SCHEMA_EXTENSIONS_FILE = SCHEMA_DIR / "00_extensions.sql"
    SCHEMA_TABLES_FILE = SCHEMA_DIR / "01_tables.sql"
    SCHEMA_INDEXES_FILE = SCHEMA_DIR / "02_indexes.sql"

class BookGuides:
    """Book guides constants."""
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

# TODO: these might need to be moved to the settings file
# things that are where they are right now are mostly for testing and development
class IngestionConstants:
    """Constants for ingestion."""
    APPROXIMATE_LOAD_LIMIT = 5000
    BATCH_SIZE = 10
    TESTING_LIMIT = 100