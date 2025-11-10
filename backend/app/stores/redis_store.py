import logging

from typing import Any, Optional

class RedisJSONStore:
    """Adds JSON helpers on top of base RedisStore."""

    def __init__(self, redis, default_ttl: Optional[int] = None):
        self.redis = redis
        self.default_ttl = default_ttl
        self.logger = logging.getLogger(self.__class__.__name__)

    async def json_set(
        self,
        key: str,
        value: Any,
        *,
        path: str = "$",
        ex: Optional[int] = None,
    ):
        """Set JSON at path (default root '$')."""
        if self.redis is None:
            raise ConnectionError("Redis is unavailable")
        
        await self.redis.json().set(key, path, value)
        if ex or self.default_ttl:
            await self.redis.expire(key, ex or self.default_ttl)

    async def json_get(
        self,
        key: str,
        *,
        path: str = "$",
    ) -> Any:
        """Get JSON from key (default root '$')."""
        if self.redis is None:
            return None
        data = await self.redis.json().get(key, path)
        return data[0] if data else None

    async def json_arrappend(
        self,
        key: str,
        *values: Any,
        path: str = "$",
    ) -> int:
        """Append one or more items to a JSON array at path (default root '$')."""
        if self.redis is None:
            raise ConnectionError("Redis is unavailable")
        return await self.redis.json().arrappend(key, path, *values)

    async def json_arrpop(
        self,
        key: str,
        index: int = -1,
        *,
        path: str = "$",
    ) -> Any:
        """
        Pop (remove and return) an item from a JSON array.
        By default pops the last element (`index=-1`).
        """
        if self.redis is None:
            raise ConnectionError("Redis is unavailable")
        return await self.redis.json().arrpop(key, path, index)
    
class RedisHashStore:
    """Adds HASH helpers on top of base Redis."""

    def __init__(self, redis, default_ttl: Optional[int] = None):
        self.redis = redis
        self.default_ttl = default_ttl
        self.logger = logging.getLogger(self.__class__.__name__)

    async def hset(self, key: str, mapping: dict[str, Any], ex: Optional[int] = None):
        """Set one or more hash fields."""
        if self.redis is None:
            raise ConnectionError("Redis is unavailable")
        if not mapping:
            return 0

        await self.redis.hset(key, mapping=mapping)

        if ex or self.default_ttl:
            await self.redis.expire(key, ex or self.default_ttl)

    async def hget(self, key: str, field: str) -> Optional[str]:
        """Get a single field from the hash."""
        if self.redis is None:
            return None
        return await self.redis.hget(key, field)

    async def hgetall(self, key: str) -> dict[str, str]:
        """Get all fields in the hash."""
        if self.redis is None:
            return {}
        return await self.redis.hgetall(key)

    async def hdel(self, key: str, *fields: str) -> int:
        """Delete one or more fields from the hash."""
        if self.redis is None:
            raise ConnectionError("Redis is unavailable")
        return await self.redis.hdel(key, *fields)

    async def hexists(self, key: str, field: str) -> bool:
        """Check if a field exists in the hash."""
        if self.redis is None:
            return False
        return await self.redis.hexists(key, field)

    async def hincrby(self, key: str, field: str, amount: int = 1) -> int:
        """Increment an integer field by amount."""
        if self.redis is None:
            raise ConnectionError("Redis is unavailable")
        return await self.redis.hincrby(key, field, amount)