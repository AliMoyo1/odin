from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.models import Project
from app.schemas.projects import ProjectCreate, ProjectPatch


def _validate_workspace_path(relative: str) -> Path:
    root = Path(settings.WORKSPACE_ROOT).resolve()
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        raise HTTPException(400, "workspace_path escapes the workspace root")
    return candidate


async def create_project(session: AsyncSession, user_id: str, body: ProjectCreate) -> Project:
    if body.workspace_path:
        abs_path = _validate_workspace_path(body.workspace_path)
        abs_path.mkdir(parents=True, exist_ok=True)

    project = Project(
        user_id=user_id,
        name=body.name,
        description=body.description,
        workspace_path=body.workspace_path,
    )
    session.add(project)
    await session.commit()
    await session.refresh(project)
    return project


async def list_projects(
    session: AsyncSession,
    user_id: str,
    include_archived: bool = False,
) -> list[Project]:
    q = select(Project).where(Project.user_id == user_id)
    if not include_archived:
        q = q.where(Project.is_active == True)
    q = q.order_by(Project.created_at.desc())
    result = await session.execute(q)
    return list(result.scalars().all())


async def get_project(session: AsyncSession, user_id: str, project_id: str) -> Project:
    result = await session.execute(
        select(Project).where(Project.id == project_id, Project.user_id == user_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(404, "Project not found")
    return project


async def patch_project(
    session: AsyncSession, user_id: str, project_id: str, body: ProjectPatch
) -> Project:
    project = await get_project(session, user_id, project_id)
    if body.name is not None:
        project.name = body.name
    if body.description is not None:
        project.description = body.description
    if body.workspace_path is not None:
        abs_path = _validate_workspace_path(body.workspace_path)
        abs_path.mkdir(parents=True, exist_ok=True)
        project.workspace_path = body.workspace_path
    await session.commit()
    await session.refresh(project)
    return project


async def archive_project(session: AsyncSession, user_id: str, project_id: str) -> Project:
    project = await get_project(session, user_id, project_id)
    project.is_active = False
    await session.commit()
    await session.refresh(project)
    return project
