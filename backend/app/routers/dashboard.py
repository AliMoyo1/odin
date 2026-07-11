import json
import os
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_session
from app.deps import get_current_user
from app.models.models import Notification, Task, User
from app.schemas.dashboard import DashboardOut, PriorityTask, RecentFile
from app.services.events import _get_async

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])

_SKIP_DIRS = {".stversions", ".git"}
_MAX_ENTRIES = 10_000


def _recent_files(workspace_root: str, top: int = 5) -> list[RecentFile]:
    root = Path(workspace_root)
    if not root.exists():
        return []

    files: list[tuple[float, str, int]] = []
    count = 0

    def _walk(path: Path, depth: int) -> None:
        nonlocal count
        if depth > 6 or count >= _MAX_ENTRIES:
            return
        try:
            entries = list(os.scandir(path))
        except PermissionError:
            return
        for entry in entries:
            if count >= _MAX_ENTRIES:
                return
            count += 1
            name = entry.name
            if name.startswith(".sync-conflict") or name in _SKIP_DIRS:
                continue
            if entry.is_dir(follow_symlinks=False):
                _walk(Path(entry.path), depth + 1)
            else:
                try:
                    stat = entry.stat()
                    rel = str(Path(entry.path).relative_to(root))
                    files.append((stat.st_mtime, rel, stat.st_size))
                except (OSError, ValueError):
                    pass

    _walk(root, 0)
    files.sort(key=lambda x: x[0], reverse=True)
    return [RecentFile(path=f[1], size=f[2], mtime=f[0]) for f in files[:top]]


@router.get("", response_model=DashboardOut)
async def get_dashboard(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    priority_result = await session.execute(
        select(Task)
        .where(
            Task.user_id == user.id,
            Task.status.in_(["todo", "in_progress"]),
        )
        .order_by(
            Task.priority.desc(),
            Task.due_date.asc().nulls_last(),
        )
        .limit(5)
    )
    priority_tasks = [
        PriorityTask(
            id=str(t.id),
            title=t.title,
            status=t.status,
            priority=t.priority,
            due_date=t.due_date,
            project_id=str(t.project_id) if t.project_id else None,
        )
        for t in priority_result.scalars().all()
    ]

    recent = _recent_files(settings.WORKSPACE_ROOT)

    r = _get_async()
    try:
        raw = await r.hgetall("runs:active")
        running_tasks = list(raw.values()) if raw else []
    except Exception:
        running_tasks = []

    unread_result = await session.execute(
        select(Notification).where(
            Notification.user_id == user.id, Notification.read == False
        )
    )
    unread_count = len(unread_result.scalars().all())

    email_name = user.email.split("@")[0]

    return DashboardOut(
        greeting_name=email_name,
        server_time_utc=datetime.now(timezone.utc),
        priorities=priority_tasks,
        recent_files=recent,
        running_tasks=running_tasks,
        unread_notifications=unread_count,
    )
