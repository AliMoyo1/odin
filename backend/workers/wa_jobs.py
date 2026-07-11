from __future__ import annotations

import logging
import os
from pathlib import Path

from sqlalchemy import select

from app.db import async_session
from app.hermes import loop
from app.models.models import Conversation, Message
from app.services import conversation_service, transcribe, tts, wa_client
from app.schemas.conversations import ConversationCreate

logger = logging.getLogger(__name__)

_WA_CONV_REDIS_KEY = "wa:conv:{user_id}"
_WA_CONV_TITLE = "WhatsApp"
_WA_MAX_REPLY_LEN = 3900
_WA_HARD_CAP = 4096


async def handle_inbound(msg: dict, user_id: str) -> None:
    msg_type = msg.get("type", "")
    from_num = msg.get("from", "")
    wamid = msg.get("id", "")

    conv_id = await _get_or_create_wa_conv(user_id)

    if msg_type == "text":
        text_body = msg.get("text", {}).get("body", "")
        if not text_body:
            return
        logger.info("WA inbound text wamid=%s len=%d", wamid, len(text_body))
        await _process_text(text_body, user_id, conv_id, from_num, voice_origin=False)

    elif msg_type == "audio":
        audio_meta = msg.get("audio", {})
        media_id = audio_meta.get("id", "")
        duration = int(audio_meta.get("duration", 0))

        if duration > 300:
            await wa_client.send_text(from_num, "That voice note is too long for me (5 minute limit).")
            return

        logger.info("WA inbound audio wamid=%s media_id=%s duration=%d", wamid, media_id, duration)
        if not media_id:
            return

        if not transcribe.settings.OPENAI_API_KEY:
            await wa_client.send_text(
                from_num,
                "Voice notes need the transcription service, which is not configured.",
            )
            return

        transcript = await transcribe.fetch_and_transcribe(media_id, duration_seconds=duration)
        if transcript is None:
            await wa_client.send_text(from_num, "That voice note is too long for me (5 minute limit).")
            return
        if not transcript:
            await wa_client.send_text(from_num, "I could not transcribe that voice note.")
            return

        logger.info("WA transcribed wamid=%s len=%d", wamid, len(transcript))
        await _process_text(transcript, user_id, conv_id, from_num, voice_origin=True)

    else:
        await wa_client.send_text(from_num, "I can handle text and voice notes for now.")


async def _process_text(
    text: str,
    user_id: str,
    conv_id: str,
    from_num: str,
    voice_origin: bool,
) -> None:
    async with async_session() as session:
        msg = await conversation_service.append_message(
            session, conv_id, "user", text, metadata={"source": "whatsapp"}
        )
        msg_id = str(msg.id)

    await loop.run_turn(user_id, conv_id, msg_id)

    async with async_session() as session:
        result = await session.execute(
            select(Message)
            .where(Message.conversation_id == conv_id, Message.role == "assistant")
            .order_by(Message.created_at.desc())
            .limit(1)
        )
        asst_msg = result.scalar_one_or_none()

    if not asst_msg or not asst_msg.content:
        return

    reply_text = asst_msg.content

    if voice_origin:
        audio_path = await tts.maybe_speak(reply_text, voice_origin=True)
        if audio_path:
            try:
                await wa_client.send_audio(from_num, audio_path)
            finally:
                try:
                    os.unlink(audio_path)
                except OSError:
                    pass
            if len(reply_text.split()) >= tts._MAX_WORDS:
                summary = reply_text[:200].rstrip() + "..."
                await wa_client.send_text(
                    from_num, f"Long answer, full version on the dashboard: {summary}"
                )
            return

    if len(reply_text) > _WA_MAX_REPLY_LEN:
        reply_text = reply_text[:_WA_MAX_REPLY_LEN] + "\n\n(continued on the dashboard)"

    await wa_client.send_text(from_num, reply_text)


async def _get_or_create_wa_conv(user_id: str) -> str:
    import redis.asyncio as aioredis
    from app.config import settings as _settings

    r = aioredis.from_url(_settings.REDIS_URL, decode_responses=True)
    try:
        redis_key = _WA_CONV_REDIS_KEY.format(user_id=user_id)
        conv_id = await r.get(redis_key)

        if conv_id:
            async with async_session() as session:
                result = await session.execute(
                    select(Conversation).where(
                        Conversation.id == conv_id, Conversation.user_id == user_id
                    )
                )
                conv = result.scalar_one_or_none()
                if conv is not None:
                    return conv_id

        async with async_session() as session:
            conv = Conversation(user_id=user_id, title=_WA_CONV_TITLE)
            session.add(conv)
            await session.commit()
            await session.refresh(conv)
            new_id = str(conv.id)

        await r.set(redis_key, new_id)
        return new_id
    finally:
        await r.aclose()
