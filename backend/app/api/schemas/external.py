from pydantic import BaseModel

class SessionOut(BaseModel):
    id: str
    created_at: str

class ChatIn(BaseModel):
    message: str

class HealthStatus(BaseModel):
    """Health check response model."""

    postgres: bool = False
    redis: bool = False
    openai: bool = False
    orchestrator: bool = False
    sqlalchemy_engine: bool = False
    message: str = "Service status"