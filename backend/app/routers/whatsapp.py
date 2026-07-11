from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
from collections import deque

import redis.asyncio as aioredis
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse, Response

from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/integrations/whatsapp", tags=["whatsapp"])

# Dedup: bounded deque + mirror set (O(1) lookup, O(1) eviction)
_DEDUP_MAX = 500
_dedup_deque: deque[str] = deque(maxlen=_DEDUP_MAX)
_dedup_set: set[str] = set()

# Rate limit: 10 messages per 60-second window per sender
_RL_LIMIT = 10
_RL_WINDOW = 60

# Cached single user id (ODIN is single-user)
_user_id_cache: str | None = None


def _dedup_add(wamid: str) -> bool:
    """Add wamid to dedup store. Returns True if already seen (duplicate)."""
    if wamid in _dedup_set:
        return True
    if len(_dedup_deque) == _dedup_deque.maxlen:
        evicted = _dedup_deque[0]
        _dedup_set.discard(evicted)
    _dedup_deque.append(wamid)
    _dedup_set.add(wamid)
    return False


async def _get_user_id() -> str:
    global _user_id_cache
    if _user_id_cache:
        return _user_id_cache
    from sqlalchemy import text
    from app.db import async_session
    async with async_session() as session:
        result = await session.execute(text("SELECT id FROM users LIMIT 1"))
        row = result.fetchone()
        if not row:
            raise RuntimeError("No users in database")
        _user_id_cache = str(row[0])
    return _user_id_cache


async def _check_rate_limit(r, from_num: str) -> bool:
    """Returns True if over limit."""
    key = f"rl:wa:{from_num}"
    count = await r.incr(key)
    if count == 1:
        await r.expire(key, _RL_WINDOW)
    return count > _RL_LIMIT


async def _handle_inbound_safe(msg: dict, user_id: str) -> None:
    try:
        from workers.wa_jobs import handle_inbound
        await handle_inbound(msg, user_id)
    except Exception:
        logger.exception("WA inbound handler failed wamid=%s", msg.get("id"))


@router.get("/webhook")
async def verify_webhook(request: Request):
    if not settings.WHATSAPP_VERIFY_TOKEN:
        raise HTTPException(503, "WhatsApp verify token not configured")

    mode = request.query_params.get("hub.mode", "")
    token = request.query_params.get("hub.verify_token", "")
    challenge = request.query_params.get("hub.challenge", "")

    if mode != "subscribe":
        raise HTTPException(403, "Invalid mode")

    if not hmac.compare_digest(token, settings.WHATSAPP_VERIFY_TOKEN):
        raise HTTPException(403, "Token mismatch")

    return PlainTextResponse(challenge)


@router.post("/webhook")
async def inbound_webhook(request: Request):
    if not settings.WHATSAPP_APP_SECRET:
        raise HTTPException(503, "WhatsApp app secret not configured")

    # MUST read raw bytes before any other body access
    raw = await request.body()

    header = request.headers.get("X-Hub-Signature-256", "")
    expected = "sha256=" + hmac.new(
        settings.WHATSAPP_APP_SECRET.encode(), raw, hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(header, expected):
        raise HTTPException(401, "Signature mismatch")

    # All exceptions after this point must still return 200
    try:
        payload = json.loads(raw)
        entry = payload.get("entry", [{}])
        changes = entry[0].get("changes", [{}]) if entry else [{}]
        value = changes[0].get("value", {}) if changes else {}
        messages = value.get("messages")

        # Status updates (delivery receipts etc.) have no messages key
        if not messages:
            return Response(status_code=200)

        msg = messages[0]
        wamid = msg.get("id", "")
        from_num = msg.get("from", "")

        # Dedup
        if _dedup_add(wamid):
            logger.debug("WA dedup hit wamid=%s", wamid)
            return Response(status_code=200)

        # Binding: only process the owner's number
        if from_num != settings.WHATSAPP_ALLOWED_NUMBER:
            logger.info("unbound_wa_sender from=%s wamid=%s", from_num, wamid)
            return Response(status_code=200)

        # Rate limit
        r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        try:
            over = await _check_rate_limit(r, from_num)
            if over:
                warn_key = f"rl:wa:warned:{from_num}"
                already_warned = await r.exists(warn_key)
                if not already_warned:
                    await r.setex(warn_key, _RL_WINDOW, "1")
                    asyncio.create_task(
                        wa_client_send_slow_down(from_num)
                    )
                return Response(status_code=200)
        finally:
            await r.aclose()

        user_id = await _get_user_id()
        asyncio.create_task(_handle_inbound_safe(msg, user_id))

    except Exception:
        logger.exception("WA webhook processing error (returning 200 to Meta)")

    return Response(status_code=200)


async def wa_client_send_slow_down(from_num: str) -> None:
    from app.services import wa_client
    try:
        await wa_client.send_text(from_num, "Slow down a little.")
    except Exception:
        logger.exception("WA rate-limit reply failed")
