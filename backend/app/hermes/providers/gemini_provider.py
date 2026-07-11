from __future__ import annotations

import copy
import json
from typing import AsyncIterator

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

_GEMINI_SCHEMA_DROP = {"additionalProperties", "$schema"}
_GEMINI_ALLOWED_FORMATS = {"enum", "date-time"}


def _sanitize_schema(schema: dict) -> dict:
    if not isinstance(schema, dict):
        return schema
    result = {}
    for k, v in schema.items():
        if k in _GEMINI_SCHEMA_DROP:
            continue
        if k == "format" and v not in _GEMINI_ALLOWED_FORMATS:
            continue
        if isinstance(v, dict):
            result[k] = _sanitize_schema(v)
        elif isinstance(v, list):
            result[k] = [_sanitize_schema(item) if isinstance(item, dict) else item for item in v]
        else:
            result[k] = v
    return result


class GeminiProvider:
    name = "gemini"

    def __init__(self) -> None:
        self._client = None

    @property
    def configured(self) -> bool:
        return bool(settings.GEMINI_API_KEY)

    def _get_client(self):
        if self._client is None:
            from google import genai
            self._client = genai.Client(api_key=settings.GEMINI_API_KEY)
        return self._client

    def _build_contents(self, messages: list[ChatMessage]) -> list:
        from google.genai import types as gtypes
        contents = []
        pending_tool_results: list = []

        for msg in messages:
            if msg.role == "system":
                continue

            if msg.role == "tool_result":
                pending_tool_results.append(
                    gtypes.Part.from_function_response(
                        name=msg.metadata.get("tool_name", "unknown"),
                        response={"result": str(msg.content or "")},
                    )
                )
                continue

            if pending_tool_results:
                contents.append(gtypes.Content(role="user", parts=pending_tool_results))
                pending_tool_results = []

            if msg.role == "user":
                text = msg.content if isinstance(msg.content, str) else json.dumps(msg.content)
                contents.append(gtypes.Content(role="user", parts=[gtypes.Part.from_text(text=text)]))
            elif msg.role == "assistant":
                text = msg.content if isinstance(msg.content, str) else str(msg.content or "")
                contents.append(gtypes.Content(role="model", parts=[gtypes.Part.from_text(text=text)]))

        if pending_tool_results:
            contents.append(gtypes.Content(role="user", parts=pending_tool_results))

        return contents

    def _build_tools(self, tools: list[ToolSpec]):
        if not tools:
            return None
        from google.genai import types as gtypes
        decls = []
        for t in tools:
            schema = _sanitize_schema(copy.deepcopy(t.input_schema))
            decls.append(gtypes.FunctionDeclaration(
                name=t.name,
                description=t.description,
                parameters=schema,
            ))
        return [gtypes.Tool(function_declarations=decls)]

    async def stream_turn(
        self,
        system: str,
        messages: list[ChatMessage],
        tools: list[ToolSpec],
        max_tokens: int,
    ) -> AsyncIterator[TextDelta | ToolCallReady | TurnDone]:
        try:
            from google.genai import types as gtypes
            client = self._get_client()
            contents = self._build_contents(messages)
            gemini_tools = self._build_tools(tools)

            config_kwargs: dict = {
                "max_output_tokens": max_tokens,
                "system_instruction": system,
            }
            if gemini_tools:
                config_kwargs["tools"] = gemini_tools

            config = gtypes.GenerateContentConfig(**config_kwargs)
            usage: dict = {}
            tool_calls_emitted: list[ToolCall] = []
            stop_reason = "STOP"

            async for chunk in await client.aio.models.generate_content_stream(
                model=settings.GEMINI_MODEL,
                contents=contents,
                config=config,
            ):
                if chunk.usage_metadata:
                    usage = {
                        "input_tokens": chunk.usage_metadata.prompt_token_count or 0,
                        "output_tokens": chunk.usage_metadata.candidates_token_count or 0,
                    }

                if not chunk.candidates:
                    continue

                for cand in chunk.candidates:
                    if cand.finish_reason:
                        stop_reason = str(cand.finish_reason)
                    if not cand.content or not cand.content.parts:
                        continue
                    for part in cand.content.parts:
                        if part.text:
                            yield TextDelta(text=part.text)
                        elif part.function_call:
                            fc = part.function_call
                            args = dict(fc.args) if fc.args else {}
                            tc = ToolCall(id=fc.name, name=fc.name, arguments=args)
                            tool_calls_emitted.append(tc)
                            yield ToolCallReady(call=tc)

            yield TurnDone(stop_reason=stop_reason, usage=usage, raw_content=None)

        except ProviderError:
            raise
        except Exception as e:
            raise ProviderError("gemini", retriable=True, message=str(e)) from e
