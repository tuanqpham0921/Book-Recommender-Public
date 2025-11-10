import logging

from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

from app.common.utils import _examples


logger = logging.getLogger(__name__)


class InitialParseBase(BaseModel):
    user_query: str = Field(
        ...,
        description="Original user query",
    )
    small_talk: Optional[str] = Field(None, description="Small talk in the request")
    out_of_scope: Optional[str] = Field(None, description="Out-of-domain content")
    user_query_domain: Optional[str] = Field(
        None, description="In-domain content (books/projects)"
    )
    reasoning: Optional[str] = Field(None, description="Reasoning for classification")


class InitialParseResult(InitialParseBase):
    continue_pipeline: bool = Field(
        default=False, description="Should the pipeline continue?"
    )


class InitialParseNode(InitialParseBase):
    domain_confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confidence between 0 and 1 that query is domain-related",
    )

    # model_config = ConfigDict(json_schema_extra=_examples)

    async def __call__(self, confident_tuning: float = 0.5) -> InitialParseResult:
        """Convert request into a result, applying confidence threshold."""
        return InitialParseResult(
            user_query=self.user_query,
            small_talk=self.small_talk,
            out_of_scope=self.out_of_scope,
            user_query_domain=self.user_query_domain,
            reasoning=self.reasoning,
            continue_pipeline=(
                True
                if self.domain_confidence >= confident_tuning and self.user_query_domain
                else False
            ),
        )
