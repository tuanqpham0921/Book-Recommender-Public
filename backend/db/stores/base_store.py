from typing import TypeVar, Generic, List, Optional, Any, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from abc import ABC, abstractmethod

T = TypeVar('T')

class BaseStore(Generic[T], ABC):
    """Base store with common database operations."""
    
    def __init__(self, session: AsyncSession, model_class: type[T]):
        self.session = session
        self.model = model_class
    
    async def get_by_id(self, id: Any) -> Optional[T]:
        """Get entity by primary key."""
        return await self.session.get(self.model, id)
    
    async def get_all(self, limit: int = 100) -> List[T]:
        """Get all entities with limit."""
        stmt = select(self.model).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def count(self) -> int:
        """Count total entities."""
        from sqlalchemy import func
        stmt = select(func.count(self.model.id))
        result = await self.session.execute(stmt)
        return result.scalar()
    
    @abstractmethod
    def row_to_dict(self, row: T) -> Dict[str, Any]:
        """Convert model instance to dictionary."""
        pass