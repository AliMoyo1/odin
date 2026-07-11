"""Workspace watcher daemon.

Run as: python -m app.watcher.daemon
Watches WORKSPACE_ROOT for file changes and enqueues indexing tasks.
"""
from __future__ import annotations

import asyncio
import logging
import threading
import time
from pathlib import Path

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer
from watchdog.observers.polling import PollingObserver

from app.config import settings
from app.services.file_service import (
    KB_EXTENSIONS,
    is_sync_conflict,
    should_skip,
    workspace_root,
)

logger = logging.getLogger(__name__)

_DEBOUNCE_SECONDS = 2.0


class _DebounceHandler(FileSystemEventHandler):
    def __init__(self) -> None:
        super().__init__()
        self._pending: dict[str, float] = {}
        self._lock = threading.Lock()

    def _schedule(self, path: str) -> None:
        with self._lock:
            self._pending[path] = time.monotonic() + _DEBOUNCE_SECONDS

    def on_created(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._schedule(event.src_path)

    def on_modified(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._schedule(event.src_path)

    def on_deleted(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._handle_delete(event.src_path)

    def on_moved(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._schedule(event.dest_path)
            self._handle_delete(event.src_path)

    def _handle_delete(self, path: str) -> None:
        rel = _to_rel(path)
        if rel is None:
            return
        asyncio.run(_async_mark_deleted(rel))

    def drain_pending(self) -> None:
        now = time.monotonic()
        with self._lock:
            ready = [p for p, t in self._pending.items() if now >= t]
            for p in ready:
                del self._pending[p]

        for path in ready:
            _handle_path(path)


def _to_rel(abs_path: str) -> str | None:
    try:
        return str(Path(abs_path).relative_to(workspace_root()))
    except ValueError:
        return None


def _handle_path(abs_path: str) -> None:
    p = Path(abs_path)

    # Skip directories and temporary/hidden files
    if p.is_dir():
        return
    if should_skip(p.name):
        return

    # Skip .trash directory
    try:
        parts = p.relative_to(workspace_root()).parts
        if any(part.startswith(".trash") or part.startswith(".stversions") for part in parts):
            return
    except ValueError:
        return

    rel = _to_rel(abs_path)
    if rel is None:
        return

    ext = p.suffix.lower().lstrip(".")

    if is_sync_conflict(p.name):
        asyncio.run(_async_conflict_notify(rel, p.name))
        return

    if ext in KB_EXTENSIONS:
        asyncio.run(_async_upsert_and_enqueue(rel, p.name))


async def _async_upsert_and_enqueue(rel_path: str, file_name: str) -> None:
    from sqlalchemy import select as sa_select
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.models.models import KnowledgeDocument, User

    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    sm = async_sessionmaker(engine, expire_on_commit=False)

    try:
        async with sm() as session:
            # Find the user for this workspace (single-user system)
            user_result = await session.execute(sa_select(User).limit(1))
            user = user_result.scalar_one_or_none()
            if user is None:
                logger.warning("watcher: no user found, cannot index %s", rel_path)
                return

            result = await session.execute(
                sa_select(KnowledgeDocument).where(
                    KnowledgeDocument.user_id == user.id,
                    KnowledgeDocument.file_path == rel_path,
                )
            )
            doc = result.scalar_one_or_none()
            if doc is None:
                full = workspace_root() / rel_path
                size = full.stat().st_size if full.exists() else None
                doc = KnowledgeDocument(
                    user_id=user.id,
                    file_path=rel_path,
                    file_name=file_name,
                    file_size=size,
                )
                session.add(doc)
                await session.flush()
            doc_id = doc.id
            await session.commit()

        from workers.indexing import index_document
        index_document.delay(doc_id)
        logger.info("watcher: enqueued indexing for %s", rel_path)
    except Exception:
        logger.exception("watcher: error upserting %s", rel_path)
    finally:
        await engine.dispose()


async def _async_mark_deleted(rel_path: str) -> None:
    from sqlalchemy import delete as sa_delete, select as sa_select
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.models.models import KnowledgeChunk, KnowledgeDocument

    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    sm = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with sm() as session:
            result = await session.execute(
                sa_select(KnowledgeDocument).where(
                    KnowledgeDocument.file_path == rel_path
                )
            )
            doc = result.scalar_one_or_none()
            if doc is not None:
                await session.execute(
                    sa_delete(KnowledgeChunk).where(KnowledgeChunk.document_id == doc.id)
                )
                doc.processed = False
                doc.extra_meta = {**(doc.extra_meta or {}), "deleted": True}
                await session.commit()
                logger.info("watcher: marked %s as deleted", rel_path)
    except Exception:
        logger.exception("watcher: error marking deleted %s", rel_path)
    finally:
        await engine.dispose()


async def _async_conflict_notify(rel_path: str, file_name: str) -> None:
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.models.models import Notification, User
    from app.services.events import publish_sync
    from sqlalchemy import select as sa_select

    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    sm = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with sm() as session:
            user_result = await session.execute(sa_select(User).limit(1))
            user = user_result.scalar_one_or_none()
            if user is None:
                return

            from app.models.models import ActivityLog
            log = ActivityLog(
                user_id=user.id,
                action="file.conflict",
                resource_type="file",
                resource_id=rel_path,
            )
            session.add(log)

            n = Notification(
                user_id=user.id,
                title=f"File conflict detected: {file_name}. Review in the file browser.",
                category="system",
            )
            session.add(n)
            await session.flush()
            await session.commit()
            await session.refresh(n)

            publish_sync(
                f"events:{user.id}",
                "notification.new",
                {"id": str(n.id), "title": n.title, "body": None, "category": "system"},
            )
            logger.warning("watcher: sync conflict detected: %s", file_name)
    except Exception:
        logger.exception("watcher: error handling conflict %s", rel_path)
    finally:
        await engine.dispose()


def run() -> None:
    from app.logging_config import configure_logging
    configure_logging()

    root = str(workspace_root())
    handler = _DebounceHandler()

    use_polling = settings.WATCHER_FORCE_POLLING
    ObserverClass = PollingObserver if use_polling else Observer
    observer = ObserverClass()
    observer.schedule(handler, root, recursive=True)
    observer.start()

    mode = "PollingObserver" if use_polling else "inotify Observer"
    logger.info("watcher: started %s on %s", mode, root)

    try:
        while True:
            handler.drain_pending()
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        observer.stop()
        observer.join()
        logger.info("watcher: stopped")


if __name__ == "__main__":
    run()
