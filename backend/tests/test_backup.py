"""Tests for backup_database job."""
from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy import delete, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.models.models import Backup


@pytest_asyncio.fixture
async def backup_engine():
    engine = create_async_engine(settings.DATABASE_URL)
    sm = async_sessionmaker(engine, expire_on_commit=False)
    yield engine, sm
    await engine.dispose()


@pytest.mark.asyncio
async def test_backup_creates_file_and_row(tmp_path, monkeypatch, backup_engine):
    """backup_database creates a dump file and a matching backups row."""
    engine, sm = backup_engine

    monkeypatch.setattr(settings, "BACKUP_LOCAL_DIR", str(tmp_path))
    monkeypatch.setattr(settings, "BACKUP_OFFSITE_REMOTE", "")
    monkeypatch.setattr(settings, "BACKUP_RETENTION_DAYS", 30)

    # Clean up any existing test rows
    async with sm() as session:
        await session.execute(delete(Backup))
        await session.commit()

    from workers.backup_jobs import _async_backup
    await _async_backup()

    # At least one dump file
    dumps = list(tmp_path.glob("odin_*.dump"))
    assert len(dumps) >= 1, "Expected at least one dump file"
    dump_file = dumps[0]
    assert dump_file.stat().st_size > 0

    expected_sha = hashlib.sha256(dump_file.read_bytes()).hexdigest()

    # Backup row exists with matching sha
    async with sm() as session:
        result = await session.execute(
            text("SELECT sha256, filename FROM backups WHERE filename = :fn"),
            {"fn": dump_file.name},
        )
        row = result.fetchone()

    assert row is not None, "Expected a backups row"
    assert row[0] == expected_sha, "SHA-256 mismatch between file and DB row"

    # Cleanup
    async with sm() as session:
        await session.execute(delete(Backup))
        await session.commit()


@pytest.mark.asyncio
async def test_retention_deletes_old_backups(tmp_path, monkeypatch, backup_engine):
    """Old backup files and their DB rows are removed by retention."""
    engine, sm = backup_engine

    monkeypatch.setattr(settings, "BACKUP_LOCAL_DIR", str(tmp_path))
    monkeypatch.setattr(settings, "BACKUP_OFFSITE_REMOTE", "")
    monkeypatch.setattr(settings, "BACKUP_RETENTION_DAYS", 30)

    async with sm() as session:
        await session.execute(delete(Backup))
        await session.commit()

    # Plant a fake old backup file (40 days old)
    old_file = tmp_path / "odin_20260101_000000.dump"
    old_file.write_bytes(b"fake old dump")
    old_date = datetime.now(timezone.utc) - timedelta(days=40)

    async with sm() as session:
        old_row = Backup(
            filename=old_file.name,
            size_bytes=len(b"fake old dump"),
            sha256=hashlib.sha256(b"fake old dump").hexdigest(),
        )
        session.add(old_row)
        await session.commit()

    # Update created_at to 40 days ago
    async with sm() as session:
        await session.execute(
            text("UPDATE backups SET created_at = :dt WHERE filename = :fn"),
            {"dt": old_date, "fn": old_file.name},
        )
        await session.commit()

    from workers.backup_jobs import _apply_retention
    await _apply_retention(tmp_path)

    # Old file deleted
    assert not old_file.exists(), "Old backup file should be deleted"

    # Old row gone
    async with sm() as session:
        result = await session.execute(
            text("SELECT id FROM backups WHERE filename = :fn"),
            {"fn": old_file.name},
        )
        assert result.fetchone() is None, "Old backup row should be removed"

    # Cleanup
    async with sm() as session:
        await session.execute(delete(Backup))
        await session.commit()


@pytest.mark.asyncio
async def test_blank_offsite_remote_does_not_fail(tmp_path, monkeypatch, backup_engine):
    """Job completes normally when BACKUP_OFFSITE_REMOTE is empty."""
    engine, sm = backup_engine

    monkeypatch.setattr(settings, "BACKUP_LOCAL_DIR", str(tmp_path))
    monkeypatch.setattr(settings, "BACKUP_OFFSITE_REMOTE", "")
    monkeypatch.setattr(settings, "BACKUP_RETENTION_DAYS", 30)

    async with sm() as session:
        await session.execute(delete(Backup))
        await session.commit()

    from workers.backup_jobs import _async_backup
    # Should not raise
    await _async_backup()

    dumps = list(tmp_path.glob("odin_*.dump"))
    assert len(dumps) >= 1

    async with sm() as session:
        await session.execute(delete(Backup))
        await session.commit()
