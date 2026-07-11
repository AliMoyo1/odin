from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import get_current_user
from app.models.models import User
from app.routers._origin import get_origin
from app.schemas.tasks import (
    SubtaskCreate,
    SubtaskOut,
    SubtaskPatch,
    TaskCreate,
    TaskOut,
    TaskPatch,
)
from app.services import task_service

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])
subtask_router = APIRouter(prefix="/api/v1/subtasks", tags=["tasks"])


@router.post("", response_model=TaskOut, status_code=201)
async def create_task(
    body: TaskCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await task_service.create_task(session, user.id, body)


@router.get("", response_model=list[TaskOut])
async def list_tasks(
    project_id: str | None = Query(None),
    status: str | None = Query(None),
    priority: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await task_service.list_tasks(
        session, user.id, project_id, status, priority, limit, offset
    )


@router.get("/{task_id}", response_model=TaskOut)
async def get_task(
    task_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await task_service.get_task(session, user.id, task_id)


@router.patch("/{task_id}", response_model=TaskOut)
async def update_task(
    task_id: str,
    body: TaskPatch,
    origin: str = Depends(get_origin),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await task_service.update_task(session, user.id, task_id, body, source=origin)


@router.delete("/{task_id}", status_code=204)
async def delete_task(
    task_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    await task_service.delete_task(session, user.id, task_id)


@router.post("/{task_id}/subtasks", response_model=SubtaskOut, status_code=201)
async def create_subtask(
    task_id: str,
    body: SubtaskCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await task_service.create_subtask(session, user.id, task_id, body.title)


@subtask_router.patch("/{subtask_id}", response_model=SubtaskOut)
async def patch_subtask(
    subtask_id: str,
    body: SubtaskPatch,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await task_service.patch_subtask(session, user.id, subtask_id, body.title, body.done)


@subtask_router.delete("/{subtask_id}", status_code=204)
async def delete_subtask(
    subtask_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    await task_service.delete_subtask(session, user.id, subtask_id)
