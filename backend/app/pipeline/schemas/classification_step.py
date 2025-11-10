import logging

from dataclasses import dataclass, field
from typing import Callable, Optional
from pydantic import BaseModel

from app.common.messages import SystemMessage
from app.orchestration.request_context import RequestContext


logger = logging.getLogger(__name__)


@dataclass
class ClassificationStep:
    """Configuration for a single classification pass (domain / strategy / tasks).

    before: hook to mutate tool JSON schema before sending (e.g. restrict enums).
    after: hook to post-process parsed model instance.
    """

    request_schema: BaseModel
    result_schema: BaseModel
    system_message: SystemMessage
    loadingMessage: str = "Thinking ..."  # noqa: N815 (retain external name)

    # TODO: double check this
    before: Optional[Callable[[dict, RequestContext], None]] = None
    after: Optional[Callable[[BaseModel, RequestContext], None]] = None
