from __future__ import annotations

import json

from pydantic import BaseModel

from app.hermes.tools.registry import registry


class RememberInput(BaseModel):
    key: str
    value: str


class RecallInput(BaseModel):
    query: str


async def _remember(inputs: RememberInput) -> str:
    return json.dumps({"ok": False, "message": "Memory engine not installed yet. Available in PLAN-06."})


async def _recall(inputs: RecallInput) -> str:
    return json.dumps({"ok": False, "message": "Memory engine not installed yet. Available in PLAN-06."})


registry.register("remember", "Store a memory for future reference", RememberInput, _remember)
registry.register("recall", "Recall relevant memories", RecallInput, _recall)
