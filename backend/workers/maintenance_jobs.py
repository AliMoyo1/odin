from __future__ import annotations

import asyncio
import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.models.models import KnowledgeDocument, Notification, Task, WsTicket
from app.services.events import publish_sync
from workers.celery_app import app as celery_app

logger = logging.getLogger(__name__)

_engine = create_async_engine(settings.DATABASE_URL, echo=False)
_sm = async_sessionmaker(_engine, expire_on_commit=False)


@celery_app.task(name="stale_task_cleanup")
def stale_task_cleanup() -> None:
    asyncio.run(_async_stale_cleanup())


@celery_app.task(name="knowledge_reindex")
def knowledge_reindex() -> None:
    asyncio.run(_async_reindex())


@celery_app.task(name="ws_ticket_cleanup")
def ws_ticket_cleanup() -> None:
    asyncio.run(_async_ws_cleanup())


async def _get_user_id() -> str | None:
    async with _sm() as session:
        result = await session.execute(text("SELECT id FROM users LIMIT 1"))
        row = result.fetchone()
        return str(row[0]) if row else None


async def _async_stale_cleanup() -> None:
    user_id = await _get_user_id()
    if not user_id:
        return

    async with _sm() as session:
        # Archive tasks that are done for > 14 days (use updated_at, not created_at)
        await session.execute(
            text("""
                UPDATE tasks
                SET status = 'archived'
                WHERE user_id = :uid
                  AND status = 'done'
                  AND updated_at < (now() - interval '14 days')
            """),
            {"uid": user_id},
        )

        # Find in_progress tasks untouched for > 7 days
        result = await session.execute(
            text("""
                SELECT id, title FROM tasks
                WHERE user_id = :uid
                  AND status = 'in_progress'
                  AND updated_at < (now() - interval '7 days')
            """),
            {"uid": user_id},
        )
        stale_in_progress = result.mappings().all()
        await session.commit()

    if stale_in_progress:
        titles = ", ".join(r["title"][:40] for r in stale_in_progress[:5])
        async with _sm() as session:
            n = Notification(
                user_id=user_id,
                title=f"{len(stale_in_progress)} in-progress task(s) untouched for 7+ days: {titles}",
                category="system",
            )
            session.add(n)
            await session.commit()
            await session.refresh(n)
            publish_sync(
                f"events:{user_id}",
                "notification.new",
                {"id": str(n.id), "title": n.title, "body": None, "category": "system"},
            )

    logger.info(
        "stale_task_cleanup: archived done tasks > 14 days old; %d in-progress tasks flagged",
        len(stale_in_progress),
    )


async def _async_reindex() -> None:
    user_id = await _get_user_id()
    if not user_id:
        return

    async with _sm() as session:
        result = await session.execute(
            select(KnowledgeDocument).where(
                KnowledgeDocument.user_id == user_id,
                KnowledgeDocument.processed.is_(True),
            )
        )
        docs = result.scalars().all()

    workspace = Path(settings.WORKSPACE_ROOT)
    enqueued = 0
    for doc in docs:
        try:
            file_path = workspace / doc.file_path
            if not file_path.exists():
                continue

            mtime = file_path.stat().st_mtime
            indexed_ts = doc.indexed_at.timestamp() if doc.indexed_at else 0.0

            # mtime check first (cheap)
            if mtime <= indexed_ts:
                continue

            # sha check to confirm real content change (not just metadata touch)
            sha = hashlib.sha256(file_path.read_bytes()).hexdigest()
            if sha == doc.content_sha256:
                continue

            from workers.indexing import index_document
            index_document.delay(str(doc.id))
            enqueued += 1
            logger.info("knowledge_reindex: enqueued reindex for %s", doc.file_name)
        except Exception as exc:
            logger.warning("knowledge_reindex: error checking %s: %s", doc.file_path, exc)

    logger.info("knowledge_reindex: checked %d docs, enqueued %d", len(docs), enqueued)


async def _async_ws_cleanup() -> None:
    async with _sm() as session:
        result = await session.execute(
            text("""
                DELETE FROM ws_tickets
                WHERE used = TRUE
                   OR expires_at < (now() - interval '1 hour')
            """)
        )
        await session.commit()
    logger.info("ws_ticket_cleanup: complete")
