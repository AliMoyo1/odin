from __future__ import annotations

import json

from pydantic import BaseModel

from app.hermes.tools.registry import registry


class RememberInput(BaseModel):
    key: str
    value: str


class RecallInput(BaseModel):
    query: str


async def _remember(
    inputs: RememberInput,
    session=None,
    user_id: str | None = None,
) -> str:
    if session is None or not user_id:
        return json.dumps({"ok": False, "error": "no database session"})
    try:
        from app.services.memory_service import store_explicit
        m = await store_explicit(session, user_id, inputs.key, inputs.value)
        return json.dumps({"ok": True, "id": m.id, "key": m.key, "value": m.value})
    except Exception as exc:
        return json.dumps({"ok": False, "error": str(exc)})


async def _recall(
    inputs: RecallInput,
    session=None,
    user_id: str | None = None,
) -> str:
    if session is None or not user_id:
        return json.dumps({"ok": False, "error": "no database session"})
    try:
        from app.services.memory_service import recall
        results = await recall(session, user_id, inputs.query)
        if not results:
            return json.dumps({"ok": True, "memories": [], "message": "No relevant memories found."})
        memories = [{"key": r.key, "value": r.value, "distance": r.distance} for r in results]
        return json.dumps({"ok": True, "memories": memories})
    except Exception as exc:
        return json.dumps({"ok": False, "error": str(exc)})


registry.register(
    "remember",
    "Store a durable personal fact for the user (preferences, environment, recurring entities). "
    "Use only for long-lived user-level facts, not transient task information.",
    RememberInput,
    _remember,
)
registry.register(
    "recall",
    "Retrieve personal facts from memory relevant to the query.",
    RecallInput,
    _recall,
)
