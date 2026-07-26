"""Redis client and health check."""

import redis.asyncio as aioredis

from src.core.config import settings

redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)


async def check_redis() -> str:
    """Health check: verify Redis connectivity."""
    try:
        await redis_client.ping()
        return "connected"
    except Exception as e:
        return f"error: {e}"
