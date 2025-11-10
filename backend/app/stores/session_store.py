import logging
from typing import Any

from app.common.types.session import SuffixEnum, StorageType
from .redis_store import RedisJSONStore, RedisHashStore

logger = logging.getLogger(__name__)

class SessionStore:
    """Orchestrates Redis backends (String, Hash, JSON) behind a unified API."""

    def __init__(self, redis, prefix: str = "session", env: str = "dev"):
        self.redis = redis
        self.prefix = prefix
        self.env = env
        
        # Backends
        self.string_backend = redis
        self.hash_backend = RedisHashStore(redis)
        self.json_backend = RedisJSONStore(redis)

        # Registry: suffix enum -> storage type
        self.registry: dict[SuffixEnum, StorageType] = {}

    def key(self, session_id: str, suffix: SuffixEnum) -> str:
        """Standard key naming."""
        return f"{self.env}:{self.prefix}:{session_id}:{suffix.value}"

    def register(self, suffix: SuffixEnum, storage_type: StorageType):
        """Register which backend a suffix uses."""
        self.registry[suffix] = storage_type
        
    def register_many(self, storage_config):
        for suffix, storage_type in storage_config.items():
            self.register(suffix, storage_type)


    # --------------------
    # Generic API
    # --------------------

    async def set(self, session_id: str, suffix: SuffixEnum, value: Any):
        key = self.key(session_id, suffix)
        stype = self.registry.get(suffix)
        if stype == StorageType.STRING:
            return await self.string_backend.set(key, value)
        elif stype == StorageType.HASH:
            return await self.hash_backend.hset(key, value)
        elif stype == StorageType.JSON:
            return await self.json_backend.json_set(key, value)
        else:
            raise ValueError(f"Suffix {suffix} not registered")

    async def get(self, session_id: str, suffix: SuffixEnum):
        key = self.key(session_id, suffix)
        stype = self.registry.get(suffix)
        if stype == StorageType.STRING:
            return await self.string_backend.get(key)
        elif stype == StorageType.HASH:
            return await self.hash_backend.hgetall(key)
        elif stype == StorageType.JSON:
            return await self.json_backend.json_get(key)
        else:
            raise ValueError(f"Suffix {suffix} not registered")

    async def delete(self, session_id: str, suffix: SuffixEnum):
        key = self.key(session_id, suffix)
        stype = self.registry.get(suffix)
        if stype == StorageType.STRING:
            return await self.string_backend.delete(key)
        elif stype == StorageType.HASH:
            return await self.hash_backend.hdel(key, *[])  # delete all fields
        elif stype == StorageType.JSON:
            return await self.redis.delete(key)
        else:
            raise ValueError(f"Suffix {suffix} not registered")

    # --------------------
    # Array (JSON only)
    # --------------------
    async def arrappend(self, session_id: str, suffix: SuffixEnum, value: Any):
        if self.registry[suffix] != StorageType.JSON:
            raise TypeError(f"Suffix {suffix} not JSON")
        key = self.key(session_id, suffix)
        return await self.json_backend.json_arrappend(key, value)

    async def arrpop(self, session_id: str, suffix: SuffixEnum, index: int = -1):
        if self.registry[suffix] != StorageType.JSON:
            raise TypeError(f"Suffix {suffix} not JSON")
        key = self.key(session_id, suffix)
        return await self.json_backend.json_arrpop(key, index)

    # --------------------
    # List (STRING-LIST hybrid, for conversation history)
    # --------------------
    async def list_rpush(self, session_id: str, suffix: SuffixEnum, *values: str):
        key = self.key(session_id, suffix)
        return await self.redis.rpush(key, *values)

    async def list_range(
        self, session_id: str, suffix: SuffixEnum, start: int = 0, end: int = -1
    ):
        key = self.key(session_id, suffix)
        return await self.redis.lrange(key, start, end)
