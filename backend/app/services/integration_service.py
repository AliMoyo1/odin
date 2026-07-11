from __future__ import annotations

import json
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.models import IntegrationConfig
from app.services.crypto import decrypt, encrypt

logger = logging.getLogger(__name__)

KNOWN_SERVICES = {"cloudflare", "hetzner", "github"}


async def set_credentials(
    session: AsyncSession, user_id: str, service: str, creds: dict
) -> IntegrationConfig:
    encrypted = encrypt(json.dumps(creds))
    result = await session.execute(
        select(IntegrationConfig).where(
            IntegrationConfig.user_id == user_id,
            IntegrationConfig.name == service,
        )
    )
    ic = result.scalar_one_or_none()
    if ic:
        ic.credentials_enc = encrypted
        ic.enabled = True
    else:
        ic = IntegrationConfig(
            user_id=user_id,
            name=service,
            credentials_enc=encrypted,
            enabled=True,
        )
        session.add(ic)
    await session.commit()
    await session.refresh(ic)
    return ic


async def get_credentials(
    session: AsyncSession, user_id: str, service: str
) -> dict | None:
    result = await session.execute(
        select(IntegrationConfig).where(
            IntegrationConfig.user_id == user_id,
            IntegrationConfig.name == service,
            IntegrationConfig.enabled.is_(True),
        )
    )
    ic = result.scalar_one_or_none()
    if ic and ic.credentials_enc:
        try:
            return json.loads(decrypt(ic.credentials_enc))
        except Exception:
            logger.error("integration_service: failed to decrypt creds for %s/%s", user_id, service)
            return None
    return _env_fallback(service)


def _env_fallback(service: str) -> dict | None:
    if service == "cloudflare" and settings.CLOUDFLARE_API_TOKEN:
        return {"token": settings.CLOUDFLARE_API_TOKEN}
    if service == "hetzner" and settings.HETZNER_API_TOKEN:
        return {"token": settings.HETZNER_API_TOKEN}
    if service == "github" and settings.GITHUB_TOKEN:
        return {"token": settings.GITHUB_TOKEN}
    return None


async def list_integrations(session: AsyncSession, user_id: str) -> list[dict]:
    result = await session.execute(
        select(IntegrationConfig).where(IntegrationConfig.user_id == user_id)
    )
    rows = result.scalars().all()
    stored = {ic.name: ic.enabled for ic in rows}
    out = []
    for svc in KNOWN_SERVICES:
        if svc in stored:
            out.append({"service": svc, "status": "connected" if stored[svc] else "disabled"})
        elif _env_fallback(svc):
            out.append({"service": svc, "status": "connected_via_env"})
        else:
            out.append({"service": svc, "status": "not_configured"})
    return out


async def delete_integration(session: AsyncSession, user_id: str, service: str) -> None:
    result = await session.execute(
        select(IntegrationConfig).where(
            IntegrationConfig.user_id == user_id,
            IntegrationConfig.name == service,
        )
    )
    ic = result.scalar_one_or_none()
    if ic:
        await session.delete(ic)
        await session.commit()
