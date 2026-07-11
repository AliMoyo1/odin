from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.models import ActivityLog

KB_EXTENSIONS: frozenset[str] = frozenset({
    "pdf", "docx", "txt", "md", "html", "csv",
    "json", "py", "js", "ts", "yaml", "yml", "xml",
})

UPLOAD_ALLOWLIST: frozenset[str] = KB_EXTENSIONS | {"png", "jpg", "jpeg"}

_TRASH_SUBDIR = ".trash"
_SKIP_DIRS: frozenset[str] = frozenset({".stversions", ".trash"})
_SKIP_PREFIXES: tuple[str, ...] = ("~$",)
_SKIP_SUFFIXES: tuple[str, ...] = (".tmp", ".part")


def resolve_in_workspace(relative: str) -> Path:
    """Resolve `relative` inside WORKSPACE_ROOT. Raises ValueError if outside."""
    if "\x00" in relative:
        raise ValueError("null byte in path")
    if os.path.isabs(relative):
        raise ValueError("absolute path not allowed")
    root = Path(settings.WORKSPACE_ROOT).resolve()
    candidate = (root / relative).resolve()
    candidate.relative_to(root)  # raises ValueError if escapes root
    return candidate


def workspace_root() -> Path:
    return Path(settings.WORKSPACE_ROOT).resolve()


def is_kb_type(extension: str) -> bool:
    return extension.lower().lstrip(".") in KB_EXTENSIONS


def is_allowed_upload(extension: str) -> bool:
    return extension.lower().lstrip(".") in UPLOAD_ALLOWLIST


def should_skip(name: str) -> bool:
    """Return True for paths that should never be indexed or listed."""
    if name.startswith(".stversions") or name.startswith(_TRASH_SUBDIR):
        return True
    if any(name.startswith(p) for p in _SKIP_PREFIXES):
        return True
    if any(name.endswith(s) for s in _SKIP_SUFFIXES):
        return True
    return False


async def log_file_activity(
    session: AsyncSession,
    user_id: str,
    action: str,
    file_path: str,
) -> None:
    entry = ActivityLog(
        user_id=user_id,
        action=action,
        resource_type="file",
        resource_id=file_path,
    )
    session.add(entry)
    # Caller commits


def trash_path(name: str) -> Path:
    """Return the trash path with a timestamp prefix."""
    root = workspace_root()
    trash = root / _TRASH_SUBDIR
    trash.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    return trash / f"{stamp}_{name}"


def is_sync_conflict(name: str) -> bool:
    return ".sync-conflict-" in name
