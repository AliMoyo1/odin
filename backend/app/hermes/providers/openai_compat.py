from __future__ import annotations

import json
from typing import AsyncIterator

from openai import APIConnectionError, APIStatusError, AsyncOpenAI

from app.hermes.types import (
    ChatMessage,
    ProviderError,
    TextDelta,
    ToolCall,
    ToolCallReady,
    ToolSpec,
    TurnDone,
)


class OpenAICompatProvider:
    def __init__(self, name: str, api_key: str, base_url: str | None, model: str) -> None:
        self.name = name
        self._api_key = api_key
        self._base_url = base_url
        self._model = model
        self._client: AsyncOpenAI | None = None

    @property
    def configured(self) -> bool:
        return bool(self._api_key)

    def _get_client(self) -> AsyncOpenAI:
        if self._client is None:
            kwargs: dict = {"api_key": self._api_key}
            if self._base_url:
                kwargs["base_url"] = self._base_url
            self._client = AsyncOpenAI(**kwargs)
        return self._client

    def _build_api_messages(self, system: str, messages: list[ChatMessage]) -> list[dict]:
        result: list[dict] = [{"role": "system", "content": system}]

        for msg in messages:
            if msg.role == "system":
                continue

            if msg.role == "user":
                content = msg.content if isinstance(msg.content, str) else json.dumps(msg.content)
                result.append({"role": "user", "content": content})

            elif msg.role == "assistant":
                api_msg: dict = {"role": "assistant", "content": None}
                if msg.tool_calls:
                    api_msg["tool_calls"] = [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {"name": tc.name, "arguments": json.dumps(tc.arguments)},
                        }
                        for tc in msg.tool_calls
                    ]
                else:
                    api_msg["content"] = msg.content if isinstance(msg.content, str) else str(msg.content or "")
                result.append(api_msg)

            elif msg.role == "tool_result":
                result.append({
                    "role": "tool",
                    "tool_call_id": msg.tool_call_id,
                    "content": str(msg.content or ""),
                })

        return result

    async def stream_turn(
        self,
        system: str,
        messages: list[ChatMessage],
        tools: list[ToolSpec],
        max_tokens: int,
    ) -> AsyncIterator[TextDelta | ToolCallReady | TurnDone]:
        client = self._get_client()
        api_messages = self._build_api_messages(system, messages)
        api_tools = [t.as_openai() for t in tools] if tools else []

        create_kwargs: dict = dict(
            model=self._model,
            messages=api_messages,
            max_tokens=max_tokens,
            stream=True,
            stream_options={"include_usage": True},
        )
        if api_tools:
            create_kwargs["tools"] = api_tools

        try:
            # Accumulate tool call fragments keyed by index
            tool_acc: dict[int, dict] = {}  # index -> {id, name, args_parts}
            finish_reason: str | None = None
            usage: dict = {}
            text_acc = ""

            async with await client.chat.completions.create(**create_kwargs) as stream:
                async for chunk in stream:
                    if chunk.usage:
                        usage = {
                            "input_tokens": chunk.usage.prompt_tokens,
                            "output_tokens": chunk.usage.completion_tokens,
                        }

                    if not chunk.choices:
                        continue

                    choice = chunk.choices[0]

                    if choice.finish_reason:
                        finish_reason = choice.finish_reason

                    delta = choice.delta
                    if delta is None:
                        continue

                    if delta.content:
                        text_acc += delta.content
                        yield TextDelta(text=delta.content)

                    if delta.tool_calls:
                        for tc_delta in delta.tool_calls:
                            idx = tc_delta.index
                            if idx not in tool_acc:
                                tool_acc[idx] = {"id": "", "name": "", "args_parts": []}
                            entry = tool_acc[idx]
                            if tc_delta.id:
                                entry["id"] = tc_delta.id
                            if tc_delta.function:
                                if tc_delta.function.name:
                                    entry["name"] = tc_delta.function.name
                                if tc_delta.function.arguments:
                                    entry["args_parts"].append(tc_delta.function.arguments)

            if finish_reason == "tool_calls":
                for idx in sorted(tool_acc.keys()):
                    entry = tool_acc[idx]
                    raw_args = "".join(entry["args_parts"])
                    try:
                        arguments = json.loads(raw_args) if raw_args else {}
                    except json.JSONDecodeError:
                        arguments = {"_raw": raw_args}
                    yield ToolCallReady(call=ToolCall(
                        id=entry["id"],
                        name=entry["name"],
                        arguments=arguments,
                    ))

            yield TurnDone(stop_reason=finish_reason or "stop", usage=usage, raw_content=None)

        except (APIStatusError, APIConnectionError) as e:
            raise ProviderError(self.name, retriable=True, message=str(e)) from e
        except ProviderError:
            raise
        except Exception as e:
            raise ProviderError(self.name, retriable=True, message=str(e)) from e
