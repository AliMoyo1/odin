from __future__ import annotations

import logging
import os
import subprocess
import tempfile
from pathlib import Path

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_GRAPH_API = "https://graph.facebook.com/v20.0"
_MAX_DURATION_SECONDS = 300
_MAX_FILE_BYTES = 16 * 1024 * 1024  # 16 MB


def _bearer() -> dict:
    return {"Authorization": f"Bearer {settings.WHATSAPP_TOKEN}"}


async def fetch_and_transcribe(
    media_id: str,
    duration_seconds: int = 0,
) -> str | None:
    if not settings.OPENAI_API_KEY:
        return None  # caller sends the "not configured" reply

    if duration_seconds > _MAX_DURATION_SECONDS:
        return None  # caller sends the "too long" reply

    # Step 1: get the media URL (Meta two-step fetch)
    async with httpx.AsyncClient(timeout=30) as client:
        meta_resp = await client.get(f"{_GRAPH_API}/{media_id}", headers=_bearer())
        meta_resp.raise_for_status()
        meta = meta_resp.json()

    file_size = int(meta.get("file_size", 0))
    if file_size > _MAX_FILE_BYTES:
        return None  # caller sends the "too long" reply

    media_url = meta.get("url", "")
    if not media_url:
        logger.error("transcribe: no url in media metadata for %s", media_id)
        return None

    # Step 2: download the actual file WITH the auth header
    async with httpx.AsyncClient(timeout=60) as client:
        audio_resp = await client.get(media_url, headers=_bearer(), follow_redirects=True)
        audio_resp.raise_for_status()

    content_type = audio_resp.headers.get("content-type", "")
    if "audio" not in content_type and "octet-stream" not in content_type:
        logger.error(
            "transcribe: unexpected content-type %s for media %s - auth header missing on download?",
            content_type, media_id,
        )
        return None

    audio_bytes = audio_resp.content
    if len(audio_bytes) > _MAX_FILE_BYTES:
        return None

    # Convert ogg -> mp3 via ffmpeg then send to Whisper
    with tempfile.TemporaryDirectory() as tmp:
        ogg_path = Path(tmp) / "voice.ogg"
        mp3_path = Path(tmp) / "voice.mp3"
        ogg_path.write_bytes(audio_bytes)

        result = subprocess.run(
            ["ffmpeg", "-i", str(ogg_path), "-q:a", "4", str(mp3_path)],
            capture_output=True,
            timeout=60,
        )
        if result.returncode != 0:
            logger.error("transcribe: ffmpeg failed: %s", result.stderr.decode(errors="replace"))
            return None

        from openai import AsyncOpenAI
        oa = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        with open(mp3_path, "rb") as f:
            transcript = await oa.audio.transcriptions.create(model="whisper-1", file=f)

    return (transcript.text or "").strip() or None
