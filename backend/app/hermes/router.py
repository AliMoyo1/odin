from __future__ import annotations

import asyncio
import time
from typing import AsyncIterator

import structlog

from app.config import settings
from app.hermes import breaker as _breaker
from app.hermes.providers.anthropic_provider import AnthropicProvider
from app.hermes.providers.gemini_provider import GeminiProvider
from app.hermes.providers.openai_compat import OpenAICompatProvider
from app.hermes.types import (
    ChatMessage,
    ProviderError,
    TextDelta,
    ToolCallReady,
    ToolSpec,
    TurnDone,
)
from app.metrics import llm_call_duration_seconds

logger = structlog.get_logger(service="router")

_CALL_TIMEOUT = 30.0   # seconds to first token
_STREAM_TIMEOUT = 120.0  # total stream guard


def _build_providers() -> list:
    return [
        OpenAICompatProvider(
            name="deepseek",
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL,
            model=settings.DEEPSEEK_MODEL,
        ),
        AnthropicProvider(),
        GeminiProvider(),
        OpenAICompatProvider(
            name="openai",
            api_key=settings.OPENAI_API_KEY,
            base_url=None,
            model=settings.OPENAI_MODEL,
        ),
        OpenAICompatProvider(
            name="ollama",
            api_key="ollama",
            base_url=settings.OLLAMA_BASE_URL + "/v1",
            model=settings.OLLAMA_MODEL,
        ),
    ]


_providers = _build_providers()


async def stream_with_failover(
    system: str,
    messages: list[ChatMessage],
    tools: list[ToolSpec],
    max_tokens: int = 4096,
) -> AsyncIterator[TextDelta | ToolCallReady | TurnDone]:
    candidates = [p for p in _providers if p.configured and _breaker.is_available(p.name)]

    if not candidates:
        logger.error("all_providers_unavailable")
        yield TurnDone(stop_reason="error", usage={}, raw_content=None)
        return

    for provider in candidates:
        text_emitted = False
        buffered: list = []

        try:
            t0 = time.monotonic()
            got_first = False

            async with asyncio.timeout(_STREAM_TIMEOUT):
                async for event in provider.stream_turn(system, messages, tools, max_tokens):
                    buffered.append(event)
                    if isinstance(event, TextDelta):
                        if not got_first:
                            elapsed = time.monotonic() - t0
                            if elapsed > _CALL_TIMEOUT:
                                raise TimeoutError(f"first token timeout after {elapsed:.1f}s")
                            llm_call_duration_seconds.labels(provider=provider.name).observe(elapsed)
                            got_first = True
                        text_emitted = True

            _breaker.record_success(provider.name)
            logger.info("provider_served", provider=provider.name)
            for ev in buffered:
                yield ev
            return

        except (ProviderError, TimeoutError, asyncio.TimeoutError) as exc:
            _breaker.record_failure(provider.name)
            logger.warning("provider_failed", provider=provider.name, error=str(exc), text_emitted=text_emitted)
            if text_emitted:
                for ev in buffered:
                    yield ev
                yield TurnDone(stop_reason="error", usage={}, raw_content=None)
                return

        except Exception as exc:
            _breaker.record_failure(provider.name)
            logger.error("provider_unexpected", provider=provider.name, error=str(exc))
            if text_emitted:
                for ev in buffered:
                    yield ev
                yield TurnDone(stop_reason="error", usage={}, raw_content=None)
                return

    logger.error("all_candidates_exhausted")
    yield TurnDone(stop_reason="error", usage={}, raw_content=None)
