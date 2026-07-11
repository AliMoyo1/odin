from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel


class TaskStatus(StrEnum):
    backlog = "backlog"
    todo = "todo"
    in_progress = "in_progress"
    blocked = "blocked"
    done = "done"
    cancelled = "cancelled"


class TaskPriority(StrEnum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class TaskCreate(BaseModel):
    title: str
    description: str | None = None
    project_id: str | None = None
    status: TaskStatus = TaskStatus.backlog
    priority: TaskPriority = TaskPriority.medium
    due_date: datetime | None = None
    tags: list[str] | None = None


class TaskPatch(BaseModel):
    title: str | None = None
    description: str | None = None
    project_id: str | None = None
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    due_date: datetime | None = None
    tags: list[str] | None = None


class TaskOut(BaseModel):
    id: str
    user_id: str
    project_id: str | None
    title: str
    description: str | None
    status: str
    priority: str
    due_date: datetime | None
    completed_at: datetime | None
    tags: list | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SubtaskCreate(BaseModel):
    title: str


class SubtaskPatch(BaseModel):
    title: str | None = None
    done: bool | None = None


class SubtaskOut(BaseModel):
    id: str
    task_id: str
    title: str
    done: bool
    position: int
    created_at: datetime

    model_config = {"from_attributes": True}


class ChangelogOut(BaseModel):
    id: str
    task_id: str
    user_id: str | None
    field_name: str
    old_value: str | None
    new_value: str | None
    changed_at: datetime

    model_config = {"from_attributes": True}
