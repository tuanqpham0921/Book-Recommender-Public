import logging
from typing import Any, AsyncGenerator

from fastapi import Request, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.stores.book_store import BookStore
from app.clients import OpenAIClient
from app.stores.session_store import SessionStore
from app.state.state_manager import StateManager
from app.orchestration.orchestrator import Orchestrator

logger = logging.getLogger(__name__)


def get_postgres_pool(request: Request) -> Any:
    """Get the asyncpg connection pool"""
    pool = getattr(request.app.state, "pg_pool", None)
    if pool is None:
        raise HTTPException(status_code=503, detail="PostgreSQL pool not available")
    return pool


def get_redis(request: Request) -> Any:
    """Get the Redis client"""
    redis_client = getattr(request.app.state, "redis", None)
    if redis_client is None:
        raise HTTPException(status_code=503, detail="Redis client not available")
    return redis_client


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


def get_session_store(request: Request) -> SessionStore:
    """Get the session store"""
    store = getattr(request.app.state, "session_store", None)
    if store is None:
        raise HTTPException(status_code=503, detail="Session store not available")
    return store


def get_state_manager(request: Request) -> StateManager:
    """Get a state manager instance"""
    store = get_session_store(request)
    return StateManager(store)


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
    pg_pool=Depends(get_postgres_pool),
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
            # state_manager=state_manager,
            pg_pool=pg_pool,
            session=session,
            book_store=book_store,
            sse_stream=sse_stream,
        )

    return create_context


def get_core_services(request: Request) -> tuple[Any, Any, OpenAIClient, Orchestrator]:
    """Get all core services at once"""
    return (
        get_postgres_pool(request),
        get_redis(request),
        get_openai_client(request),
        get_orchestrator(request),
    )


async def get_database_services(
    pg_pool=Depends(get_postgres_pool),
    session: AsyncSession = Depends(get_sqlalchemy_session),
) -> tuple[Any, AsyncSession]:
    """Get both database services."""
    return pg_pool, session
