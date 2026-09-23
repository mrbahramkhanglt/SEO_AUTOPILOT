"""Optional Redis cache – degrades gracefully if Redis is down."""
from __future__ import annotations

import json
import logging
import random
from typing import Any, Optional

from app.core.config import get_settings

logger = logging.getLogger("seo.cache")
_client = None
_failed = False


async def get_redis():
    global _client, _failed
    if _failed:
        return None
    if _client is not None:
        return _client
    settings = get_settings()
    url = getattr(settings, "redis_url", None) or ""
    if not url or url.startswith("memory"):
        return None
    try:
        import redis.asyncio as redis

        _client = redis.from_url(url, decode_responses=True)
        await _client.ping()
        return _client
    except Exception as e:
        logger.warning("Redis unavailable, cache disabled: %s", e)
        _failed = True
        return None


def _jitter(ttl: int) -> int:
    if ttl <= 1:
        return ttl
    return max(1, ttl + random.randint(-int(ttl * 0.1), int(ttl * 0.1)))


async def cache_get(key: str) -> Optional[Any]:
    r = await get_redis()
    if not r:
        return None
    try:
        raw = await r.get(key)
        return json.loads(raw) if raw else None
    except Exception:
        return None


async def cache_set(key: str, value: Any, ttl: int = 300) -> None:
    r = await get_redis()
    if not r:
        return
    try:
        await r.setex(key, _jitter(ttl), json.dumps(value, default=str))
    except Exception as e:
        logger.debug("cache_set failed: %s", e)


async def cache_delete(*keys: str) -> None:
    r = await get_redis()
    if not r or not keys:
        return
    try:
        await r.delete(*keys)
    except Exception:
        pass


async def cache_delete_pattern(prefix: str) -> None:
    """Best-effort delete by prefix (use sparingly)."""
    r = await get_redis()
    if not r:
        return
    try:
        async for key in r.scan_iter(match=f"{prefix}*"):
            await r.delete(key)
    except Exception:
        pass
