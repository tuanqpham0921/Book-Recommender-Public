import logging

from redis.asyncio import Redis

from app.config import settings

# from app.stores import RedisJSONStore

logger = logging.getLogger(__name__)


async def init_redis() -> Redis | None:
    try:
        rdb = Redis(
            host=settings.redis.HOST, port=settings.redis.PORT, decode_responses=True
        )
        await rdb.ping()
        return rdb
    except Exception as e:
        return None


async def close_redis(rdb: Redis | None):
    if rdb:
        await rdb.close()
        logger.info("Redis closed")
