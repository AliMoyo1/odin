from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

import redis.asyncio as aioredis

from app.config import settings
from app.hermes.types import ToolCall

_GATE_TTL = 600  # seconds
_KEY_PREFIX = "gate:"


def _r() -> aioredis.Redis:
    return aioredis.from_url(settings.REDIS_URL, decode_responses=True)


async def create_gate(
    conversation_id: str,
    user_id: str,
    project_id: str | None,
    call: ToolCall,
    provider_messages_snapshot: list,
) -> tuple[str, int]:
    """Store a pending approval. Returns (approval_id, expires_in_seconds)."""
    approval_id = str(uuid.uuid4())
    payload = json.dumps({
        "conversation_id": conversation_id,
        "user_id": user_id,
        "project_id": project_id,
        "tool_call": {
            "id": call.id,
            "name": call.name,
            "arguments": call.arguments,
        },
        "messages_snapshot": provider_messages_snapshot,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    r = _r()
    try:
        await r.set(f"{_KEY_PREFIX}{approval_id}", payload, ex=_GATE_TTL)
    finally:
        await r.aclose()
    return approval_id, _GATE_TTL


async def consume_gate(approval_id: str) -> dict | None:
    """Atomically get and delete the gate entry. Returns None if expired/missing."""
    r = _r()
    try:
        raw = await r.getdel(f"{_KEY_PREFIX}{approval_id}")
    finally:
        await r.aclose()
    if raw is None:
        return None
    return json.loads(raw)


async def gate_exists(approval_id: str) -> bool:
    r = _r()
    try:
        return await r.exists(f"{_KEY_PREFIX}{approval_id}") > 0
    finally:
        await r.aclose()
