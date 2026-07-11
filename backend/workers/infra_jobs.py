from __future__ import annotations

import asyncio
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.models.models import Notification, Task, User
from app.services.events import publish_sync
from workers.celery_app import app as celery_app

logger = logging.getLogger(__name__)

_engine = create_async_engine(settings.DATABASE_URL, echo=False)
_sm = async_sessionmaker(_engine, expire_on_commit=False)

_SSL_WARN_DAYS = 30


@celery_app.task(name="infra_audit")
def infra_audit() -> None:
    asyncio.run(_async_infra_audit())


@celery_app.task(name="ssl_cert_countdown")
def ssl_cert_countdown() -> None:
    asyncio.run(_async_ssl_countdown())


async def _get_user_id() -> str | None:
    async with _sm() as session:
        result = await session.execute(text("SELECT id FROM users LIMIT 1"))
        row = result.fetchone()
        return str(row[0]) if row else None


async def _notify(user_id: str, title: str, body: str | None, wa_alert: bool = False) -> None:
    async with _sm() as session:
        n = Notification(user_id=user_id, title=title, body=body, category="system")
        session.add(n)
        await session.commit()
        await session.refresh(n)
        publish_sync(
            f"events:{user_id}",
            "notification.new",
            {"id": str(n.id), "title": n.title, "body": n.body, "category": "system"},
        )

    if wa_alert and settings.WHATSAPP_ALLOWED_NUMBER:
        try:
            from app.services import wa_client
            await wa_client.send_text(settings.WHATSAPP_ALLOWED_NUMBER, f"ODIN infra alert: {title[:200]}")
        except Exception:
            logger.exception("infra_jobs: WA alert failed")


async def _async_infra_audit() -> None:
    user_id = await _get_user_id()
    if not user_id:
        return

    async with _sm() as session:
        from app.services.integration_service import get_credentials
        hetzner_creds = await get_credentials(session, user_id, "hetzner")
        cf_creds = await get_credentials(session, user_id, "cloudflare")

    if not hetzner_creds and not cf_creds:
        logger.info("infra_audit: no integrations configured; skipping")
        return

    issues: list[str] = []

    if hetzner_creds:
        try:
            from app.integrations.hetzner import list_servers
            servers = await list_servers(hetzner_creds["token"])
            for s in servers:
                if s.status != "running":
                    issues.append(f"Hetzner server {s.name!r} status={s.status}")
        except Exception as exc:
            logger.warning("infra_audit: Hetzner check failed: %s", exc)

    if cf_creds:
        zone_ids = cf_creds.get("zone_ids", [])
        if isinstance(zone_ids, str):
            zone_ids = [zone_ids]
        for zone_id in zone_ids:
            try:
                from app.integrations.cloudflare import recent_firewall_events
                summary = await recent_firewall_events(zone_id, cf_creds["token"])
                if summary.event_count > 500:
                    issues.append(
                        f"Cloudflare zone {zone_id}: {summary.event_count} firewall events in 24h"
                        + (f" (top countries: {', '.join(summary.top_countries)})" if summary.top_countries else "")
                    )
            except Exception as exc:
                logger.warning("infra_audit: Cloudflare zone %s check failed: %s", zone_id, exc)

    if issues:
        body = "\n".join(issues)
        high_severity = any("status=" in i and "running" not in i for i in issues)
        await _notify(user_id, f"Infra audit: {len(issues)} issue(s) found", body, wa_alert=high_severity)
        logger.warning("infra_audit: %d issues: %s", len(issues), body)
    else:
        logger.info("infra_audit: all systems healthy")


async def _async_ssl_countdown() -> None:
    user_id = await _get_user_id()
    if not user_id:
        return

    async with _sm() as session:
        from app.services.integration_service import get_credentials
        cf_creds = await get_credentials(session, user_id, "cloudflare")

    if not cf_creds:
        logger.info("ssl_cert_countdown: Cloudflare not configured; skipping")
        return

    zone_ids = cf_creds.get("zone_ids", [])
    if isinstance(zone_ids, str):
        zone_ids = [zone_ids]

    for zone_id in zone_ids:
        try:
            from app.integrations.cloudflare import get_zone_ssl
            cert = await get_zone_ssl(zone_id, cf_creds["token"])
            if cert.days_remaining is not None and cert.days_remaining < _SSL_WARN_DAYS:
                expiry_str = cert.expires_on.strftime("%Y-%m-%d") if cert.expires_on else "unknown"
                title = f"SSL certificate for zone {zone_id} expires in {cert.days_remaining} days ({expiry_str})"
                # Create high-priority task
                async with _sm() as session:
                    task = Task(
                        user_id=user_id,
                        title=f"Renew SSL for zone {zone_id}, expires {expiry_str}",
                        priority="high",
                        status="todo",
                    )
                    session.add(task)
                    await session.commit()
                await _notify(user_id, title, None, wa_alert=True)
        except Exception as exc:
            logger.warning("ssl_cert_countdown: zone %s failed: %s", zone_id, exc)
