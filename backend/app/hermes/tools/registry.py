from __future__ import annotations

import functools
import traceback
from typing import Any, Callable, Type

from pydantic import BaseModel

from app.hermes.types import ToolCall, ToolSpec

_MAX_RESULT_CHARS = 16000  # ~4000 estimated tokens


class ToolRegistry:
    def __init__(self) -> None:
        self._specs: dict[str, ToolSpec] = {}
        self._handlers: dict[str, Callable] = {}
        self._input_models: dict[str, Type[BaseModel]] = {}

    def register(
        self,
        name: str,
        description: str,
        input_model: Type[BaseModel],
        handler: Callable,
        requires_approval: bool = False,
    ) -> None:
        schema = input_model.model_json_schema()
        schema.pop("title", None)
        self._specs[name] = ToolSpec(
            name=name,
            description=description,
            input_schema=schema,
            requires_approval=requires_approval,
        )
        self._handlers[name] = handler
        self._input_models[name] = input_model

    def tool(
        self,
        name: str,
        description: str,
        requires_approval: bool = False,
    ):
        def decorator(cls_or_fn):
            if isinstance(cls_or_fn, type) and issubclass(cls_or_fn, BaseModel):
                raise TypeError("@tool decorator must wrap an async handler function, not a model class")
            return cls_or_fn
        return decorator

    def specs(self) -> list[ToolSpec]:
        return list(self._specs.values())

    def get_spec(self, name: str) -> ToolSpec | None:
        return self._specs.get(name)

    async def dispatch(self, call: ToolCall, db_session=None, user_id: str | None = None) -> str:
        handler = self._handlers.get(call.name)
        if not handler:
            return f'{{"ok": false, "error": "unknown tool: {call.name}"}}'
        model_class = self._input_models[call.name]
        try:
            inputs = model_class(**call.arguments)
            if db_session is not None:
                result = await handler(inputs, session=db_session, user_id=user_id)
            else:
                result = await handler(inputs)
            text = str(result) if not isinstance(result, str) else result
            if len(text) > _MAX_RESULT_CHARS:
                text = text[:_MAX_RESULT_CHARS] + "\n[truncated]"
            return text
        except Exception as e:
            err_type = type(e).__name__
            return f'{{"ok": false, "error": "{err_type}: {str(e)[:200]}"}}'


registry = ToolRegistry()
