"""
Smoke-test each configured LLM provider with a minimal prompt.
Run inside the container: python scripts/provider_smoke.py
"""
from __future__ import annotations

import asyncio
import sys
import time
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


async def smoke_provider(provider) -> None:
    from app.hermes.types import ChatMessage, TextDelta, TurnDone
    name = provider.name
    if not provider.configured:
        print(f"SKIP  {name}: not configured")
        return

    msg = ChatMessage(role="user", content="Reply with exactly the word: ok")
    t0 = time.monotonic()
    first_text = ""
    try:
        async for event in provider.stream_turn(
            system="You are a test assistant. Reply as instructed.",
            messages=[msg],
            tools=[],
            max_tokens=32,
        ):
            if isinstance(event, TextDelta) and not first_text:
                first_text = event.text
            elif isinstance(event, TurnDone):
                elapsed_ms = int((time.monotonic() - t0) * 1000)
                print(f"OK    {name}: {elapsed_ms}ms | {first_text[:40]!r}")
                return
    except Exception as e:
        elapsed_ms = int((time.monotonic() - t0) * 1000)
        print(f"FAIL  {name}: {elapsed_ms}ms | {e}")


async def main() -> None:
    from app.hermes.providers.anthropic_provider import AnthropicProvider
    from app.hermes.providers.gemini_provider import GeminiProvider
    from app.hermes.providers.openai_compat import OpenAICompatProvider
    from app.config import settings

    providers = [
        OpenAICompatProvider("deepseek", settings.DEEPSEEK_API_KEY, settings.DEEPSEEK_BASE_URL, settings.DEEPSEEK_MODEL),
        AnthropicProvider(),
        GeminiProvider(),
        OpenAICompatProvider("openai", settings.OPENAI_API_KEY, None, settings.OPENAI_MODEL),
        OpenAICompatProvider("ollama", "ollama", settings.OLLAMA_BASE_URL + "/v1", settings.OLLAMA_MODEL),
    ]
    for p in providers:
        await smoke_provider(p)


if __name__ == "__main__":
    asyncio.run(main())
