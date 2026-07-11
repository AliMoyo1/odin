from __future__ import annotations

from typing import AsyncIterator, Protocol, runtime_checkable

from app.hermes.types import ChatMessage, TextDelta, ToolCallReady, ToolSpec, TurnDone


@runtime_checkable
class Provider(Protocol):
    name: str
    configured: bool

    def stream_turn(
        self,
        system: str,
        messages: list[ChatMessage],
        tools: list[ToolSpec],
        max_tokens: int,
    ) -> AsyncIterator[TextDelta | ToolCallReady | TurnDone]: ...
