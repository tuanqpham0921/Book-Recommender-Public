from enum import Enum
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import re


class Intent(Enum):
    SIMILARITY_BY_TITLE = "similarity_by_title"
    SIMILARITY_BY_AUTHOR = "similarity_by_author"
    SIMILARITY_BY_TRAITS = "similarity_by_traits"
    DATABASE_STATS = "database_stats"
    AUTHOR_STATS = "author_stats"
    AMBIGUOUS_AUTHOR = "ambiguous_author"  # Needs clarification
    UNKNOWN = "unknown"


@dataclass
class Constraints:
    min_pages: Optional[int] = None
    max_pages: Optional[int] = None
    publication_year_before: Optional[int] = None
    publication_year_after: Optional[int] = None
    genre: Optional[str] = None
    age_group: Optional[str] = None  # children, ya, adult
    fiction_type: Optional[str] = None  # fiction, nonfiction


@dataclass
class QueryContext:
    """Shared context passed between strategies"""
    original_query: str
    intent: Intent
    constraints: Constraints
    reference_title: Optional[str] = None
    reference_author: Optional[str] = None
    reference_isbn: Optional[str] = None
    reference_traits: Optional[List[str]] = None
    
    # Results populated by strategies
    retrieved_books: List[Any] = None
    filtered_books: List[Any] = None
    recommendations: List[Any] = None
    stats: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.retrieved_books is None:
            self.retrieved_books = []
        if self.filtered_books is None:
            self.filtered_books = []
        if self.recommendations is None:
            self.recommendations = []


class IntentClassifier:
    """Detects user intent from query"""
    
    def classify(self, query: str) -> Intent:
        query_lower = query.lower()
        
        # Database stats queries
        if self._is_stats_query(query_lower):
            if self._mentions_author(query_lower):
                return Intent.AUTHOR_STATS
            return Intent.DATABASE_STATS
        
        # Similarity queries
        if self._is_similarity_query(query_lower):
            return self._classify_similarity_type(query_lower)
        
        return Intent.UNKNOWN
    
    def _is_stats_query(self, query: str) -> bool:
        stats_patterns = [
            r'how many',
            r'count of',
            r'total books',
            r'number of books'
        ]
        return any(re.search(pattern, query) for pattern in stats_patterns)
    
    def _is_similarity_query(self, query: str) -> bool:
        similarity_patterns = [
            r'similar to',
            r'like',
            r'books.*like',
            r'recommend.*based on',
            r'in the style of'
        ]
        return any(re.search(pattern, query) for pattern in similarity_patterns)
    
    def _mentions_author(self, query: str) -> bool:
        author_patterns = [
            r'by\s+\w+',
            r'author',
            r'stephen king',  # Add known authors
            r'written by'
        ]
        return any(re.search(pattern, query) for pattern in author_patterns)
    
    def _classify_similarity_type(self, query: str) -> Intent:
        """Determine if query is by title, author, or traits"""
        
        # Check for explicit "by" keyword indicating author
        if re.search(r'\bby\s+[\w\s]+', query):
            return Intent.SIMILARITY_BY_AUTHOR
        
        # Check for author name without "by" - AMBIGUOUS
        # "books similar to Stephen King" could mean BY or LIKE
        if self._has_potential_author_name(query):
            return Intent.AMBIGUOUS_AUTHOR
        
        # Check for quoted titles or capitalized works
        if re.search(r'"[^"]+"', query) or re.search(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', query):
            return Intent.SIMILARITY_BY_TITLE
        
        # Check for trait-based descriptions
        trait_keywords = ['dark humor', 'dystopian', 'romance', 'thriller', 'fantasy']
        if any(trait in query.lower() for trait in trait_keywords):
            return Intent.SIMILARITY_BY_TRAITS
        
        return Intent.SIMILARITY_BY_TITLE  # Default assumption
    
    def _has_potential_author_name(self, query: str) -> bool:
        """Detect if query contains a proper name that could be an author"""
        # Simple heuristic: capitalized words that aren't common book words
        common_words = {'the', 'a', 'an', 'of', 'to', 'in', 'for', 'with'}
        words = query.split()
        
        for i, word in enumerate(words):
            if word[0].isupper() and word.lower() not in common_words:
                # Check if followed by another capitalized word (likely full name)
                if i + 1 < len(words) and words[i + 1][0].isupper():
                    return True
        return False


class ConstraintExtractor:
    """Extracts filtering constraints from query"""
    
    def extract(self, query: str) -> Constraints:
        constraints = Constraints()
        
        # Extract page constraints
        page_match = re.search(r'(\d+)\s*pages?\s*or\s*more', query, re.IGNORECASE)
        if page_match:
            constraints.min_pages = int(page_match.group(1))
        
        page_match = re.search(r'(\d+)\s*pages?\s*or\s*less', query, re.IGNORECASE)
        if page_match:
            constraints.max_pages = int(page_match.group(1))
        
        # Extract year constraints
        year_match = re.search(r'before\s*(\d{4})', query, re.IGNORECASE)
        if year_match:
            constraints.publication_year_before = int(year_match.group(1))
        
        year_match = re.search(r'after\s*(\d{4})', query, re.IGNORECASE)
        if year_match:
            constraints.publication_year_after = int(year_match.group(1))
        
        year_match = re.search(r'in\s*(\d{4})', query, re.IGNORECASE)
        if year_match:
            year = int(year_match.group(1))
            constraints.publication_year_after = year
            constraints.publication_year_before = year
        
        # Extract age group
        if re.search(r'\bchildren\b|\bkids\b', query, re.IGNORECASE):
            constraints.age_group = 'children'
        elif re.search(r'\byoung adult\b|\bya\b', query, re.IGNORECASE):
            constraints.age_group = 'young_adult'
        
        # Extract fiction type
        if re.search(r'\bnonfiction\b|\bnon-fiction\b', query, re.IGNORECASE):
            constraints.fiction_type = 'nonfiction'
        elif re.search(r'\bfiction\b', query, re.IGNORECASE):
            constraints.fiction_type = 'fiction'
        
        return constraints


class ReferenceExtractor:
    """Extracts reference items (titles, authors, ISBNs) from query"""
    
    def extract_title(self, query: str) -> Optional[str]:
        # Try quoted strings first
        match = re.search(r'"([^"]+)"', query)
        if match:
            return match.group(1)
        
        # Try to extract capitalized phrase after "similar to" or "like"
        match = re.search(r'(?:similar to|like)\s+([A-Z][^,.\n]+?)(?:\s+with|\s+and|$)', query)
        if match:
            return match.group(1).strip()
        
        return None
    
    def extract_author(self, query: str) -> Optional[str]:
        # Look for "by [Author Name]"
        match = re.search(r'by\s+([\w\s]+?)(?:\s+with|\s+and|$)', query, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        
        # Look for potential author name (capitalized words)
        match = re.search(r'(?:similar to|like)\s+([A-Z][a-z]+\s+[A-Z][a-z]+)', query)
        if match:
            return match.group(1).strip()
        
        return None
    
    def extract_traits(self, query: str) -> List[str]:
        traits = []
        
        # Common trait patterns
        trait_patterns = [
            r'dark humor',
            r'dystopian',
            r'romance',
            r'thriller',
            r'fantasy',
            r'sci-fi',
            r'mystery',
            r'horror'
        ]
        
        for pattern in trait_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                traits.append(pattern)
        
        return traits


class ExecutionPlanner:
    """Creates execution plan based on intent and context"""
    
    def plan(self, context: QueryContext) -> List[str]:
        """Returns list of strategy names to execute in order"""
        
        if context.intent == Intent.DATABASE_STATS:
            return ["DatabaseStatsStrategy"]
        
        if context.intent == Intent.AUTHOR_STATS:
            return ["AuthorStatsStrategy"]
        
        if context.intent == Intent.SIMILARITY_BY_TITLE:
            plan = ["FindByTitleRetrieval"]
            if self._has_constraints(context.constraints):
                plan.append("FilterStrategy")
            plan.append("RecommendationStrategy")
            return plan
        
        if context.intent == Intent.SIMILARITY_BY_AUTHOR:
            plan = ["FindByAuthorRetrieval"]
            if self._has_constraints(context.constraints):
                plan.append("FilterStrategy")
            plan.append("RecommendationStrategy")
            return plan
        
        if context.intent == Intent.SIMILARITY_BY_TRAITS:
            plan = ["FindByTraitsRetrieval"]
            if self._has_constraints(context.constraints):
                plan.append("FilterStrategy")
            plan.append("RecommendationStrategy")
            return plan
        
        if context.intent == Intent.AMBIGUOUS_AUTHOR:
            # Return clarification needed
            return ["ClarificationStrategy"]
        
        return ["UnknownIntentStrategy"]
    
    def _has_constraints(self, constraints: Constraints) -> bool:
        return any([
            constraints.min_pages,
            constraints.max_pages,
            constraints.publication_year_before,
            constraints.publication_year_after,
            constraints.genre,
            constraints.age_group,
            constraints.fiction_type
        ])


class BookRecommenderOrchestrator:
    """Main orchestrator that coordinates the entire recommendation flow"""
    
    def __init__(self, strategy_registry: Dict[str, Any]):
        self.intent_classifier = IntentClassifier()
        self.constraint_extractor = ConstraintExtractor()
        self.reference_extractor = ReferenceExtractor()
        self.execution_planner = ExecutionPlanner()
        self.strategy_registry = strategy_registry
    
    def process_query(self, query: str) -> QueryContext:
        """Main entry point for processing a user query"""
        
        # Step 1: Classify intent
        intent = self.intent_classifier.classify(query)
        
        # Step 2: Extract constraints
        constraints = self.constraint_extractor.extract(query)
        
        # Step 3: Extract references (title, author, traits)
        context = QueryContext(
            original_query=query,
            intent=intent,
            constraints=constraints,
            reference_title=self.reference_extractor.extract_title(query),
            reference_author=self.reference_extractor.extract_author(query),
            reference_traits=self.reference_extractor.extract_traits(query)
        )
        
        # Step 4: Create execution plan
        execution_plan = self.execution_planner.plan(context)
        
        # Step 5: Execute strategies in sequence
        for strategy_name in execution_plan:
            strategy = self.strategy_registry.get(strategy_name)
            if strategy:
                context = strategy.execute(context)
        
        return context
    
    def format_response(self, context: QueryContext) -> Dict[str, Any]:
        """Format the context into a user-facing response"""
        
        if context.intent == Intent.AMBIGUOUS_AUTHOR:
            return {
                "status": "clarification_needed",
                "message": f"Did you mean books BY {context.reference_author} or books with a similar style TO {context.reference_author}?",
                "options": [
                    {"label": f"Books by {context.reference_author}", "intent": "by_author"},
                    {"label": f"Books like {context.reference_author}'s style", "intent": "similar_style"}
                ]
            }
        
        if context.intent in [Intent.DATABASE_STATS, Intent.AUTHOR_STATS]:
            return {
                "status": "success",
                "stats": context.stats
            }
        
        if context.recommendations:
            return {
                "status": "success",
                "query": context.original_query,
                "constraints_applied": self._format_constraints(context.constraints),
                "recommendations": context.recommendations,
                "total_found": len(context.recommendations)
            }
        
        return {
            "status": "no_results",
            "message": "No books found matching your criteria."
        }
    
    def _format_constraints(self, constraints: Constraints) -> Dict[str, Any]:
        result = {}
        if constraints.min_pages:
            result["min_pages"] = constraints.min_pages
        if constraints.max_pages:
            result["max_pages"] = constraints.max_pages
        if constraints.publication_year_before:
            result["published_before"] = constraints.publication_year_before
        if constraints.publication_year_after:
            result["published_after"] = constraints.publication_year_after
        if constraints.age_group:
            result["age_group"] = constraints.age_group
        if constraints.fiction_type:
            result["fiction_type"] = constraints.fiction_type
        return result


# Example usage:
if __name__ == "__main__":
    # Mock strategy registry (you'll replace with actual strategies)
    strategy_registry = {
        "FindByTitleRetrieval": None,  # Your actual strategy instances
        "FindByAuthorRetrieval": None,
        "FindByTraitsRetrieval": None,
        "FilterStrategy": None,
        "RecommendationStrategy": None,
        "DatabaseStatsStrategy": None,
        "AuthorStatsStrategy": None,
        "ClarificationStrategy": None,
        "UnknownIntentStrategy": None,
    }
    
    orchestrator = BookRecommenderOrchestrator(strategy_registry)
    
    # Test queries
    test_queries = [
        "give me books similar to Dune",
        "find me books with dark humor similar to the Iliad",
        "give me children books 300 pages or more in 1990 similar to Frankenstein",
        "books similar to Stephen King with 300 pages or more",
        "How many books by stephen king are there?",
    ]
    
    for query in test_queries:
        print(f"\nQuery: {query}")
        context = orchestrator.process_query(query)
        print(f"Intent: {context.intent}")
        print(f"Reference Title: {context.reference_title}")
        print(f"Reference Author: {context.reference_author}")
        print(f"Constraints: {context.constraints}")
        print(f"Execution Plan: {orchestrator.execution_planner.plan(context)}")