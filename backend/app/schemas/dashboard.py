from datetime import datetime

from pydantic import BaseModel


class RecentFile(BaseModel):
    path: str
    size: int
    mtime: float


class PriorityTask(BaseModel):
    id: str
    title: str
    status: str
    priority: str
    due_date: datetime | None
    project_id: str | None


class DashboardOut(BaseModel):
    greeting_name: str
    server_time_utc: datetime
    priorities: list[PriorityTask]
    recent_files: list[RecentFile]
    running_tasks: list[dict]
    unread_notifications: int
