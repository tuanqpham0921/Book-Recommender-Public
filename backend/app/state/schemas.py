"""
State-related schemas and models.
"""

from typing import Optional, List
from pydantic import BaseModel

from app.common.enums import DomainEnum
from app.common.messages import APIMessage

class Preferences(BaseModel):
    user_id: Optional[str] = None  # Optional user identifier
    # use this for now,
    general_preferences: Optional[str] = None

class SessionMeta(BaseModel):
    created: str  # always set at creation
    last_updated: Optional[str] = None
    active_domain: Optional[DomainEnum] = None


class SessionState(BaseModel):
    session_id: str
    # session_meta: SessionMeta
    user_preferences: Optional[Preferences] = None
    conversation_history: List[APIMessage] = []

    # ignore extra fields if necessary
    class Config:
        extra = "ignore"
        validate_assignment = True
