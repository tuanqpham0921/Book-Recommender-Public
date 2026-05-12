import logging
from typing import Any, AsyncGenerator

from fastapi import Request, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.stores.book_store import BookStore
from clients import OpenAIClient
from app.orchestration.orchestrator import Orchestrator

logger = logging.getLogger(__name__)


def get_openai_client(request: Request) -> OpenAIClient:
    """Get the OpenAI client"""
    client = getattr(request.app.state, "openai_client", None)
    if client is None:
        raise HTTPException(status_code=503, detail="OpenAI client not available")
    return client


def get_orchestrator(request: Request) -> Orchestrator:
    """Get the orchestrator instance"""
    orchestrator = getattr(request.app.state, "orchestrator", None)
    if orchestrator is None:
        raise HTTPException(status_code=503, detail="Orchestrator not available")
    return orchestrator


def get_sqlalchemy_engine(request: Request):
    """Get SQLAlchemy engine from app state"""
    engine = getattr(request.app.state, "sqlalchemy_engine", None)
    if engine is None:
        raise HTTPException(status_code=503, detail="SQLAlchemy engine not available")
    return engine


def get_sqlalchemy_session_factory(request: Request):
    """Get SQLAlchemy session maker"""
    session_factory = getattr(request.app.state, "sqlalchemy_session_factory", None)
    if session_factory is None:
        raise HTTPException(
            status_code=503, detail="SQLAlchemy session factory not available"
        )
    return session_factory


async def get_sqlalchemy_session(
    session_factory=Depends(get_sqlalchemy_session_factory),
) -> AsyncGenerator[AsyncSession, None]:
    """Get a SQLAlchemy session"""
    async with session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_book_store(
    session: AsyncSession = Depends(get_sqlalchemy_session),
) -> BookStore:
    """Get BookStore instance with injected session."""
    return BookStore(session)


async def get_request_context_factory(
    # state_manager: StateManager = Depends(get_state_manager),
    llm_client=Depends(get_openai_client),
    session=Depends(get_sqlalchemy_session),
    book_store=Depends(get_book_store),
):
    """Factory to create request contexts with runtime arguments."""

    def create_context(session_id: str, user_message, sse_stream=None):
        from app.orchestration.request_context import RequestContext

        return RequestContext(
            session_id=session_id,
            user_message=user_message,
            llm_client=llm_client,
            book_store=book_store,
            sse_stream=sse_stream,
        )

    return create_context


def get_core_services(request: Request) -> tuple[Any, Any, OpenAIClient, Orchestrator]:
    """Get all core services at once"""
    return (
        get_openai_client(request),
        get_orchestrator(request),
    )
