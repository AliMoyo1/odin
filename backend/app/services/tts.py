from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)

_MAX_WORDS = 300


async def maybe_speak(answer_text: str, voice_origin: bool = True) -> Path | None:
    """Generate a TTS mp3 if the turn was voice-originated and the reply is short."""
    if not voice_origin:
        return None
    if not settings.OPENAI_API_KEY:
        return None
    if not settings.TTS_ENABLED:
        return None

    word_count = len(answer_text.split())
    if word_count >= _MAX_WORDS:
        return None

    from openai import AsyncOpenAI
    oa = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    # Write to a temp file that outlives this function (caller must delete)
    tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
    tmp_path = Path(tmp.name)
    tmp.close()

    response = await oa.audio.speech.create(
        model=settings.TTS_MODEL,
        voice=settings.TTS_VOICE,
        input=answer_text,
    )
    response.write_to_file(tmp_path)
    logger.info("tts: generated %d-word reply at %s", word_count, tmp_path)
    return tmp_path
