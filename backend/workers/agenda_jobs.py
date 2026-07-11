from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, timezone

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.models.models import Notification, Task, User
from app.services.events import publish_sync
from workers.celery_app import app as celery_app

logger = logging.getLogger(__name__)

_engine = create_async_engine(settings.DATABASE_URL, echo=False)
_sm = async_sessionmaker(_engine, expire_on_commit=False)


@celery_app.task(name="morning_agenda")
def morning_agenda() -> None:
    asyncio.run(_async_agenda())


async def _async_agenda() -> None:
    today = date.today()
    today_start = datetime(today.year, today.month, today.day, tzinfo=timezone.utc)
    today_end = datetime(today.year, today.month, today.day, 23, 59, 59, tzinfo=timezone.utc)

    async with _sm() as session:
        result = await session.execute(text("SELECT id FROM users LIMIT 1"))
        row = result.fetchone()
        if not row:
            return
        user_id = str(row[0])

        # Due today
        due_result = await session.execute(
            select(Task).where(
                Task.user_id == user_id,
                Task.due_date >= today_start,
                Task.due_date <= today_end,
                Task.status.not_in(["done", "cancelled", "archived"]),
            ).order_by(Task.priority.desc()).limit(10)
        )
        due_tasks = due_result.scalars().all()

        # High/critical priority active tasks
        high_result = await session.execute(
            select(Task).where(
                Task.user_id == user_id,
                Task.priority.in_(["high", "critical"]),
                Task.status.not_in(["done", "cancelled", "archived"]),
                Task.due_date.is_(None),
            ).limit(5)
        )
        high_tasks = high_result.scalars().all()

    if not due_tasks and not high_tasks:
        logger.info("morning_agenda: nothing to report today")
        return

    lines = ["Good morning! Here's your ODIN agenda:\n"]

    if due_tasks:
        lines.append(f"Due today ({len(due_tasks)}):")
        for t in due_tasks:
            lines.append(f"  [{t.priority.upper()}] {t.title}")

    if high_tasks:
        lines.append(f"\nHigh priority ({len(high_tasks)}):")
        for t in high_tasks:
            lines.append(f"  [{t.priority.upper()}] {t.title}")

    message = "\n".join(lines)

    # In-app notification (always, so the agenda is never lost)
    async with _sm() as session:
        n = Notification(
            user_id=user_id,
            title=f"Morning agenda: {len(due_tasks)} due today, {len(high_tasks)} high priority",
            body=message,
            category="system",
        )
        session.add(n)
        await session.commit()
        await session.refresh(n)
        publish_sync(
            f"events:{user_id}",
            "notification.new",
            {"id": str(n.id), "title": n.title, "body": n.body, "category": "system"},
        )

    # WhatsApp send (handles 24h window via template fallback in wa_client)
    if settings.WHATSAPP_ALLOWED_NUMBER:
        try:
            from app.services import wa_client
            await wa_client.send_text(settings.WHATSAPP_ALLOWED_NUMBER, message[:3900])
        except Exception:
            logger.exception("morning_agenda: WA send failed (in-app notification already created)")
