from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.models.models import Backup, Notification, User
from app.services.events import publish_sync
from workers.celery_app import app as celery_app

logger = logging.getLogger(__name__)

_engine = create_async_engine(settings.DATABASE_URL, echo=False)
_sm = async_sessionmaker(_engine, expire_on_commit=False)


@celery_app.task(name="backup_database")
def backup_database() -> None:
    asyncio.run(_async_backup())


async def _async_backup() -> None:
    backup_dir = Path(settings.BACKUP_LOCAL_DIR)
    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_file = backup_dir / f"odin_{timestamp}.dump"

    # Parse DATABASE_URL for pg_dump args
    url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    parsed = urlparse(url)
    host = parsed.hostname or "database-node"
    port = str(parsed.port or 5432)
    user = parsed.username or "odin"
    password = parsed.password or ""
    dbname = parsed.path.lstrip("/")

    cmd = ["pg_dump", "-h", host, "-p", port, "-U", user, "-d", dbname, "-Fc", "-f", str(out_file)]
    env = {**os.environ, "PGPASSWORD": password}

    try:
        result = subprocess.run(cmd, env=env, capture_output=True, timeout=300)
        if result.returncode != 0:
            raise RuntimeError(result.stderr.decode(errors="replace"))
    except Exception as exc:
        logger.error("backup_database: pg_dump failed: %s", exc)
        await _notify_failure(f"Backup failed: pg_dump error: {exc}")
        return

    if not out_file.exists() or out_file.stat().st_size == 0:
        await _notify_failure("Backup failed: output file empty or missing")
        return

    # Compute SHA-256
    sha = hashlib.sha256(out_file.read_bytes()).hexdigest()
    size = out_file.stat().st_size

    # Insert backups row
    async with _sm() as session:
        row = Backup(
            filename=out_file.name,
            size_bytes=size,
            sha256=sha,
            offsite_synced=False,
        )
        session.add(row)
        await session.commit()

    logger.info("backup_database: created %s (%d bytes, sha256=%s)", out_file.name, size, sha[:12])

    # Retention: delete local backups older than BACKUP_RETENTION_DAYS
    await _apply_retention(backup_dir)

    # Offsite sync
    if settings.BACKUP_OFFSITE_REMOTE:
        await _offsite_sync(backup_dir, out_file.name)
    else:
        logger.warning("backup_database: BACKUP_OFFSITE_REMOTE not set; skipping offsite sync")


async def _apply_retention(backup_dir: Path) -> None:
    cutoff_days = settings.BACKUP_RETENTION_DAYS
    now = datetime.now(timezone.utc)
    async with _sm() as session:
        result = await session.execute(
            text("""
                SELECT id, filename, created_at FROM backups
                WHERE created_at < (now() - make_interval(days := :days))
                ORDER BY created_at ASC
            """),
            {"days": cutoff_days},
        )
        old_rows = result.mappings().all()

    for row in old_rows:
        file_path = backup_dir / row["filename"]
        if file_path.exists():
            file_path.unlink()
            logger.info("backup_database: deleted old backup %s", row["filename"])
        async with _sm() as session:
            await session.execute(
                delete(Backup).where(Backup.id == str(row["id"]))
            )
            await session.commit()


async def _offsite_sync(backup_dir: Path, latest_filename: str) -> None:
    # Copy newest 7 files only to limit bandwidth
    all_dumps = sorted(backup_dir.glob("odin_*.dump"), key=lambda p: p.stat().st_mtime, reverse=True)
    newest_7 = [str(p) for p in all_dumps[:7]]
    if not newest_7:
        return

    cmd = ["rclone", "copy", "--include", "odin_*.dump", str(backup_dir), settings.BACKUP_OFFSITE_REMOTE]
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=600)
        if result.returncode != 0:
            logger.error("backup_database: rclone failed: %s", result.stderr.decode(errors="replace"))
            await _notify_failure(f"Offsite sync failed: {result.stderr.decode(errors='replace')[:200]}")
            return

        async with _sm() as session:
            await session.execute(
                text("UPDATE backups SET offsite_synced = TRUE WHERE filename = :fn"),
                {"fn": latest_filename},
            )
            await session.commit()
        logger.info("backup_database: offsite sync complete")
    except Exception as exc:
        logger.error("backup_database: offsite sync error: %s", exc)
        await _notify_failure(f"Offsite sync error: {exc}")


async def _notify_failure(message: str) -> None:
    async with _sm() as session:
        result = await session.execute(text("SELECT id FROM users LIMIT 1"))
        row = result.fetchone()
        if not row:
            return
        user_id = str(row[0])

        n = Notification(
            user_id=user_id,
            title=f"BACKUP FAILURE: {message[:400]}",
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

    # Also send WhatsApp alert
    try:
        from app.services import wa_client
        await wa_client.send_text(settings.WHATSAPP_ALLOWED_NUMBER, f"ODIN: {message[:200]}")
    except Exception:
        logger.exception("backup_database: WA alert failed")
