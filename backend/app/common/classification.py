from typing import Generic, TypeVar, List
from pydantic import BaseModel, Field

T = TypeVar('T')

class ClassificationResult(BaseModel, Generic[T]):
    """Generic classification result for any node type."""
    accepted: List[T] = []
    refused: List[T] = []
    continue_pipeline: bool = False
    
    def get_accepted_node_ids(self):
        """Return dict of node_id -> serialized node data."""
        return {node.id: node for node in self.accepted}

class ClassificationNode(BaseModel, Generic[T]):
    """Generic classification node for any strategy type."""
    strategies: List[T] = Field(
        ...,
        max_length=15,
        description="List of strategies generated from the query")

    async def __call__(self, accepted_tuning: float = 0.7) -> ClassificationResult[T]:
        result = ClassificationResult[T]()

        for req in self.strategies:
            if req.refusal or req.confidence < accepted_tuning:
                result.refused.append(req)
            else:
                result.accepted.append(req)

        result.continue_pipeline = bool(len(result.accepted) > 0)
        return result