from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ChatMessage:
    role: str  # "user", "assistant", "system", "tool_result"
    content: Any  # str | list[dict] (Anthropic raw blocks) | None
    tool_call_id: str | None = None  # for "tool_result" messages
    tool_calls: list[ToolCall] | None = None  # assistant messages that triggered tool calls (OpenAI compat)
    metadata: dict = field(default_factory=dict)


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict


@dataclass
class ToolSpec:
    name: str
    description: str
    input_schema: dict
    requires_approval: bool = False

    def as_anthropic(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }

    def as_openai(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.input_schema,
            },
        }


@dataclass
class TextDelta:
    text: str


@dataclass
class ToolCallReady:
    call: ToolCall


@dataclass
class TurnDone:
    stop_reason: str
    usage: dict  # {"input_tokens": N, "output_tokens": N}
    raw_content: list | None = None  # Anthropic-format content blocks for verbatim replay


class ProviderError(Exception):
    def __init__(self, provider: str, retriable: bool, message: str):
        super().__init__(message)
        self.provider = provider
        self.retriable = retriable
