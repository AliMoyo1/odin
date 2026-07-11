from __future__ import annotations

import json
from typing import AsyncIterator

from anthropic import APIConnectionError, APIStatusError, AsyncAnthropic

from app.config import settings
from app.hermes.types import (
    ChatMessage,
    ProviderError,
    TextDelta,
    ToolCall,
    ToolCallReady,
    ToolSpec,
    TurnDone,
)


class AnthropicProvider:
    name = "anthropic"

    def __init__(self) -> None:
        self._client: AsyncAnthropic | None = None

    @property
    def configured(self) -> bool:
        return bool(settings.ANTHROPIC_API_KEY)

    def _get_client(self) -> AsyncAnthropic:
        if self._client is None:
            self._client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        return self._client

    def _build_api_messages(self, messages: list[ChatMessage]) -> list[dict]:
        result: list[dict] = []
        pending_tool_results: list[dict] = []

        for msg in messages:
            if msg.role == "system":
                continue

            if msg.role == "tool_result":
                pending_tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": msg.tool_call_id,
                    "content": str(msg.content or ""),
                })
                continue

            if pending_tool_results:
                result.append({"role": "user", "content": pending_tool_results})
                pending_tool_results = []

            if msg.role == "user":
                content = msg.content if isinstance(msg.content, list) else str(msg.content or "")
                result.append({"role": "user", "content": content})
            elif msg.role == "assistant":
                content = msg.content if isinstance(msg.content, list) else str(msg.content or "")
                result.append({"role": "assistant", "content": content})

        if pending_tool_results:
            result.append({"role": "user", "content": pending_tool_results})

        return result

    async def stream_turn(
        self,
        system: str,
        messages: list[ChatMessage],
        tools: list[ToolSpec],
        max_tokens: int,
    ) -> AsyncIterator[TextDelta | ToolCallReady | TurnDone]:
        client = self._get_client()
        api_messages = self._build_api_messages(messages)
        api_tools = [t.as_anthropic() for t in tools] if tools else []

        create_kwargs: dict = dict(
            model=settings.HERMES_MODEL_ANTHROPIC,
            max_tokens=max_tokens,
            system=system,
            messages=api_messages,
            thinking={"type": "adaptive"},
            stream=True,
        )
        if api_tools:
            create_kwargs["tools"] = api_tools

        try:
            current_block_type: str | None = None
            tool_id: str | None = None
            tool_name: str | None = None
            tool_json_parts: list[str] = []
            partial_text = ""
            partial_thinking = ""
            raw_content_blocks: list[dict] = []
            usage: dict = {}
            stop_reason = "end_turn"

            async with client.messages.stream(**create_kwargs) as stream:
                async for event in stream:
                    etype = event.type

                    if etype == "message_start":
                        if hasattr(event.message, "usage"):
                            usage["input_tokens"] = event.message.usage.input_tokens

                    elif etype == "content_block_start":
                        b = event.content_block
                        current_block_type = b.type
                        if b.type == "tool_use":
                            tool_id = b.id
                            tool_name = b.name
                            tool_json_parts = []
                        elif b.type == "text":
                            partial_text = ""
                        elif b.type == "thinking":
                            partial_thinking = ""

                    elif etype == "content_block_delta":
                        d = event.delta
                        if d.type == "text_delta":
                            partial_text += d.text
                            yield TextDelta(text=d.text)
                        elif d.type == "input_json_delta":
                            tool_json_parts.append(d.partial_json)
                        elif d.type == "thinking_delta":
                            partial_thinking += d.thinking

                    elif etype == "content_block_stop":
                        if current_block_type == "tool_use" and tool_id and tool_name:
                            raw_json = "".join(tool_json_parts)
                            try:
                                arguments = json.loads(raw_json) if raw_json else {}
                            except json.JSONDecodeError:
                                arguments = {"_raw": raw_json}
                            raw_content_blocks.append({
                                "type": "tool_use",
                                "id": tool_id,
                                "name": tool_name,
                                "input": arguments,
                            })
                            yield ToolCallReady(call=ToolCall(id=tool_id, name=tool_name, arguments=arguments))
                            tool_id = None
                            tool_name = None
                        elif current_block_type == "text":
                            raw_content_blocks.append({"type": "text", "text": partial_text})
                        elif current_block_type == "thinking":
                            raw_content_blocks.append({"type": "thinking", "thinking": partial_thinking, "signature": ""})

                    elif etype == "message_delta":
                        stop_reason = getattr(event.delta, "stop_reason", None) or "end_turn"
                        if hasattr(event, "usage"):
                            usage["output_tokens"] = getattr(event.usage, "output_tokens", 0)

            yield TurnDone(stop_reason=stop_reason, usage=usage, raw_content=raw_content_blocks)

        except (APIStatusError, APIConnectionError) as e:
            raise ProviderError("anthropic", retriable=True, message=str(e)) from e
        except ProviderError:
            raise
        except Exception as e:
            raise ProviderError("anthropic", retriable=True, message=str(e)) from e
