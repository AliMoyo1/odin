from __future__ import annotations

import logging
from pathlib import Path

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_WA_API = "https://graph.facebook.com/v20.0"
_TIMEOUT = 15.0
_24H_ERROR_CODE = 131047


def _headers() -> dict:
    return {"Authorization": f"Bearer {settings.WHATSAPP_TOKEN}"}


def _messages_url() -> str:
    return f"{_WA_API}/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"


async def send_text(to: str, body: str) -> str:
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": body},
    }
    if settings.WA_DRY_RUN:
        logger.info("WA DRY-RUN send_text to=%s len=%d body=%s", to, len(body), body[:100])
        return "dry_run_message_id"
    return await _post_message(to, payload)


async def send_audio(to: str, media_path: Path) -> str:
    media_id = await _upload_media(media_path)
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "audio",
        "audio": {"id": media_id},
    }
    if settings.WA_DRY_RUN:
        logger.info("WA DRY-RUN send_audio to=%s media_id=%s", to, media_id)
        return "dry_run_message_id"
    return await _post_message(to, payload)


async def send_template(to: str, template_name: str, components: list) -> str:
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": "en"},
            "components": components,
        },
    }
    if settings.WA_DRY_RUN:
        logger.info("WA DRY-RUN send_template to=%s template=%s", to, template_name)
        return "dry_run_message_id"
    return await _post_message(to, payload)


async def _post_message(to: str, payload: dict) -> str:
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        for attempt in range(2):
            try:
                resp = await client.post(_messages_url(), json=payload, headers=_headers())
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get("messages", [{}])[0].get("id", "")

                # 24-hour window exhausted: fall back to template
                if resp.status_code == 400:
                    err = resp.json().get("error", {})
                    if err.get("code") == _24H_ERROR_CODE:
                        template = getattr(settings, "WHATSAPP_ALERT_TEMPLATE", "")
                        if template:
                            logger.warning("WA 24h window closed; using template %s", template)
                            return await send_template(to, template, [
                                {"type": "body", "parameters": [
                                    {"type": "text", "text": payload.get("text", {}).get("body", "")[:60]}
                                ]}
                            ])
                        logger.warning(
                            "WA 24h window closed; no template configured. Storing as in-app notification only."
                        )
                        return ""

                if resp.status_code >= 500 and attempt == 0:
                    continue  # one retry on 5xx
                resp.raise_for_status()
            except httpx.TimeoutException:
                if attempt == 0:
                    continue
                raise
    return ""


async def _upload_media(media_path: Path) -> str:
    if settings.WA_DRY_RUN:
        logger.info("WA DRY-RUN upload_media path=%s", media_path)
        return "dry_run_media_id"
    url = f"{_WA_API}/{settings.WHATSAPP_PHONE_NUMBER_ID}/media"
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        with open(media_path, "rb") as f:
            resp = await client.post(
                url,
                headers=_headers(),
                files={"file": (media_path.name, f, "audio/mpeg")},
                data={"messaging_product": "whatsapp"},
            )
        resp.raise_for_status()
        return resp.json().get("id", "")
