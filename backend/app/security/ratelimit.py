import ipaddress

import redis.asyncio as aioredis
from fastapi import HTTPException, Request

from app.config import settings


def _is_private(ip: str) -> bool:
    try:
        return ipaddress.ip_address(ip).is_private
    except ValueError:
        return False


def _resolve_ip(request: Request) -> str:
    peer = request.client.host if request.client else "127.0.0.1"
    if _is_private(peer):
        xff = request.headers.get("X-Forwarded-For", "")
        return xff.split(",")[0].strip() if xff else peer
    return peer


async def check_auth_rate_limit(request: Request) -> None:
    ip = _resolve_ip(request)
    r = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
    try:
        key = f"rl:auth:{ip}"
        count = await r.incr(key)
        if count == 1:
            await r.expire(key, 60)
        if count > 5:
            raise HTTPException(status_code=429, detail="Too many authentication attempts. Try again in a minute.")
    finally:
        await r.aclose()
