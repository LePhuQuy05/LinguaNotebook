"""Redis client and health check."""

import redis.asyncio as aioredis
import redis as sync_redis

from src.core.config import settings

# Async client (for FastAPI)
redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)

# Sync client (for Celery workers)
sync_redis_client = sync_redis.from_url(settings.redis_url, decode_responses=True)


async def check_redis() -> str:
    """Health check: verify Redis connectivity."""
    try:
        await redis_client.ping()
        return "connected"
    except Exception as e:
        return f"error: {e}"
