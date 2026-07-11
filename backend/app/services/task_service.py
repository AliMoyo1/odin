from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Subtask, Task, TaskChangelog
from app.schemas.tasks import TaskCreate, TaskPatch
from app.services.audit import log_event
from app.services.events import publish


async def create_task(session: AsyncSession, user_id: str, body: TaskCreate) -> Task:
    task = Task(
        user_id=user_id,
        project_id=body.project_id,
        title=body.title,
        description=body.description,
        status=body.status,
        priority=body.priority,
        due_date=body.due_date,
        tags=body.tags,
    )
    session.add(task)
    await session.commit()
    await session.refresh(task)
    return task


async def list_tasks(
    session: AsyncSession,
    user_id: str,
    project_id: str | None = None,
    status: str | None = None,
    priority: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Task]:
    limit = min(limit, 200)
    q = select(Task).where(Task.user_id == user_id)
    if project_id:
        q = q.where(Task.project_id == project_id)
    if status:
        q = q.where(Task.status == status)
    if priority:
        q = q.where(Task.priority == priority)
    q = q.order_by(Task.created_at.desc()).limit(limit).offset(offset)
    result = await session.execute(q)
    return list(result.scalars().all())


async def get_task(session: AsyncSession, user_id: str, task_id: str) -> Task:
    result = await session.execute(
        select(Task).where(Task.id == task_id, Task.user_id == user_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(404, "Task not found")
    return task


async def update_task(
    session: AsyncSession,
    user_id: str,
    task_id: str,
    body: TaskPatch,
    source: str = "web",
) -> Task:
    task = await get_task(session, user_id, task_id)

    changed_fields: list[str] = []

    if body.title is not None and body.title != task.title:
        task.title = body.title
        changed_fields.append("title")

    if body.description is not None and body.description != task.description:
        task.description = body.description
        changed_fields.append("description")

    if body.project_id is not None and body.project_id != task.project_id:
        task.project_id = body.project_id
        changed_fields.append("project_id")

    if body.status is not None and body.status != task.status:
        session.add(TaskChangelog(
            task_id=task.id,
            user_id=user_id,
            field_name="status",
            old_value=task.status,
            new_value=body.status,
        ))
        if body.status == "done":
            task.completed_at = datetime.now(timezone.utc)
        task.status = body.status
        changed_fields.append("status")

    if body.priority is not None and body.priority != task.priority:
        session.add(TaskChangelog(
            task_id=task.id,
            user_id=user_id,
            field_name="priority",
            old_value=task.priority,
            new_value=body.priority,
        ))
        task.priority = body.priority
        changed_fields.append("priority")

    if body.due_date is not None and body.due_date != task.due_date:
        task.due_date = body.due_date
        changed_fields.append("due_date")

    if body.tags is not None:
        task.tags = body.tags
        changed_fields.append("tags")

    if changed_fields:
        await session.commit()
        await session.refresh(task)
        await publish(f"events:{user_id}", "task.changed", {"task_id": str(task.id)})
        await log_event(session, user_id, "task_updated",
                        resource_type="task", resource_id=task.id, source=source)
        await session.commit()
    return task


async def delete_task(session: AsyncSession, user_id: str, task_id: str) -> None:
    task = await get_task(session, user_id, task_id)
    await session.delete(task)
    await session.commit()


async def create_subtask(session: AsyncSession, user_id: str, task_id: str, title: str) -> Subtask:
    await get_task(session, user_id, task_id)
    result = await session.execute(
        select(Subtask).where(Subtask.task_id == task_id)
    )
    count = len(result.scalars().all())
    subtask = Subtask(task_id=task_id, title=title, position=count)
    session.add(subtask)
    await session.commit()
    await session.refresh(subtask)
    return subtask


async def get_subtask(session: AsyncSession, user_id: str, subtask_id: str) -> Subtask:
    result = await session.execute(
        select(Subtask).where(Subtask.id == subtask_id)
    )
    subtask = result.scalar_one_or_none()
    if not subtask:
        raise HTTPException(404, "Subtask not found")
    await get_task(session, user_id, subtask.task_id)
    return subtask


async def patch_subtask(
    session: AsyncSession, user_id: str, subtask_id: str, title: str | None, done: bool | None
) -> Subtask:
    subtask = await get_subtask(session, user_id, subtask_id)
    if title is not None:
        subtask.title = title
    if done is not None:
        subtask.done = done
    await session.commit()
    await session.refresh(subtask)
    return subtask


async def delete_subtask(session: AsyncSession, user_id: str, subtask_id: str) -> None:
    subtask = await get_subtask(session, user_id, subtask_id)
    await session.delete(subtask)
    await session.commit()
