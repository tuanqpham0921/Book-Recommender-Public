from pydantic import BaseModel, Field
from typing import List
from app.domains.books.schemas import ClassificationStrategy


class BookClassificationResult(BaseModel):
    """Generic classification result for any node type."""
    accepted: List[ClassificationStrategy] = []
    refused: List[ClassificationStrategy] = []
    continue_pipeline: bool = False
    
    def get_accepted_node_ids(self):
        """Return dict of node_id -> serialized node data."""
        return {node.id: node for node in self.accepted}


class BookClassificationNode(BaseModel):
    """Classification node specifically for book domain strategies."""
    strategies: List[ClassificationStrategy] = Field(
        ...,
        max_length=15,
        description="List of strategies generated from the query")

    async def __call__(self, accepted_tuning: float = 0.7):
        """Convert to ClassificationResult format"""        
        result = BookClassificationResult()
        
        for strategy in self.strategies:
            if strategy.refusal or strategy.confidence < accepted_tuning:
                result.refused.append(strategy)
            else:
                result.accepted.append(strategy)

        result.continue_pipeline = bool(len(result.accepted) > 0)
        return result