"""Redis-backed sliding window rate limiter."""

import time

import redis.asyncio as aioredis

from app.core.config import settings

_redis: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(
            settings.CELERY_BROKER_URL, decode_responses=True
        )
    return _redis


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        await _redis.close()
        _redis = None


async def check_rate_limit(
    key: str, max_attempts: int, window_seconds: int
) -> tuple[bool, int, int]:
    """Sliding window rate limiter using Redis sorted sets.

    Returns (allowed, remaining, retry_after_seconds).
    """
    r = await get_redis()
    now = time.time()
    window_start = now - window_seconds

    pipe = r.pipeline()
    pipe.zremrangebyscore(key, 0, window_start)
    pipe.zcard(key)
    results = await pipe.execute()

    current_count = results[1]

    if current_count >= max_attempts:
        # Find oldest entry to calculate retry_after
        oldest = await r.zrange(key, 0, 0, withscores=True)
        retry_after = int(oldest[0][1] + window_seconds - now) + 1 if oldest else window_seconds
        return False, 0, retry_after

    # Under the limit — record this attempt
    pipe2 = r.pipeline()
    pipe2.zadd(key, {str(now): now})
    pipe2.expire(key, window_seconds)
    await pipe2.execute()

    remaining = max_attempts - current_count - 1
    return True, remaining, 0
