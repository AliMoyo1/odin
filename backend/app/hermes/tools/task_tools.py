from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.hermes.tools.registry import registry
from app.services import task_service, project_service
from app.schemas.tasks import TaskCreate, TaskPatch


class CreateTaskInput(BaseModel):
    title: str
    description: str | None = None
    project_id: str | None = None
    priority: str | None = None
    due_date: str | None = None


class UpdateTaskInput(BaseModel):
    task_id: str
    status: str | None = None
    priority: str | None = None
    due_date: str | None = None
    title: str | None = None


class ListTasksInput(BaseModel):
    project_id: str | None = None
    status: str | None = None


class ListProjectsInput(BaseModel):
    pass


async def _create_task(inputs: CreateTaskInput, session: AsyncSession, user_id: str) -> str:
    body = TaskCreate(
        title=inputs.title,
        description=inputs.description,
        project_id=inputs.project_id,
        priority=inputs.priority or "medium",
    )
    task = await task_service.create_task(session, user_id, body)
    return json.dumps({"ok": True, "task_id": str(task.id), "title": task.title, "status": task.status})


async def _update_task(inputs: UpdateTaskInput, session: AsyncSession, user_id: str) -> str:
    body = TaskPatch(
        status=inputs.status,
        priority=inputs.priority,
        title=inputs.title,
    )
    task = await task_service.update_task(session, user_id, inputs.task_id, body)
    return json.dumps({"ok": True, "task_id": str(task.id), "status": task.status})


async def _list_tasks(inputs: ListTasksInput, session: AsyncSession, user_id: str) -> str:
    tasks = await task_service.list_tasks(session, user_id, project_id=inputs.project_id, status=inputs.status)
    items = [{"id": str(t.id), "title": t.title, "status": t.status, "priority": t.priority} for t in tasks[:50]]
    return json.dumps({"ok": True, "tasks": items, "count": len(items)})


async def _list_projects(inputs: ListProjectsInput, session: AsyncSession, user_id: str) -> str:
    projects = await project_service.list_projects(session, user_id)
    items = [{"id": str(p.id), "name": p.name} for p in projects]
    return json.dumps({"ok": True, "projects": items})


registry.register("create_task", "Create a new task", CreateTaskInput, _create_task)
registry.register("update_task", "Update an existing task", UpdateTaskInput, _update_task)
registry.register("list_tasks", "List tasks, optionally filtered by project or status", ListTasksInput, _list_tasks)
registry.register("list_projects", "List all projects", ListProjectsInput, _list_projects)
