import json

import redis
import redis.asyncio as aioredis

from app.config import settings

_async_client: aioredis.Redis | None = None
_sync_client: redis.Redis | None = None


def _get_async() -> aioredis.Redis:
    global _async_client
    if _async_client is None:
        _async_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    return _async_client


def _get_sync() -> redis.Redis:
    global _sync_client
    if _sync_client is None:
        _sync_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _sync_client


async def publish(channel: str, event_type: str, data: dict) -> None:
    payload = json.dumps({"type": event_type, "data": data})
    await _get_async().publish(channel, payload)


def publish_sync(channel: str, event_type: str, data: dict) -> None:
    payload = json.dumps({"type": event_type, "data": data})
    _get_sync().publish(channel, payload)
