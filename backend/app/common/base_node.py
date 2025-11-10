from uuid import uuid4
from pydantic import BaseModel, Field
from typing import Optional, List

from app.domains.books.types import NodeType


class BaseNode(BaseModel):
    # Only require what the user/LLM must provide
    description: str = Field(
        ..., description="Description of query that attributes to this strategy"
    )

    # Everything else is optional or auto-generated
    reasoning: Optional[str] = Field(
        default=None, description="Reasoning for strategy selection"
    )
    # inferences: str = Field(default=None, description="Any inference or correction from the query")
    confidence: float = Field(
        default=0.0, description="Confidence score for the parsed results"
    )
    refusal: bool = Field(default=False, description="Did we refuse this strategy type")
    id: str = Field(default="", description="Auto-generated unique identifier")
    depends_on: List[str] = Field(
        default_factory=list, description="List of task IDs this task depends on"
    )

    def get_type(self) -> Optional[NodeType]:
        """Override in subclasses to return the specific node type."""
        if hasattr(self, "node_type"):
            return self.node_type
        return None

    def model_post_init(self, __context) -> None:
        """Auto-generate ID if not provided."""
        if not self.id:
            base_id = str(uuid4())[:8]
            self.id = base_id
