from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import get_current_user
from app.models.models import User
from app.schemas.projects import ProjectCreate, ProjectOut, ProjectPatch
from app.services import project_service

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


@router.post("", response_model=ProjectOut, status_code=201)
async def create_project(
    body: ProjectCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await project_service.create_project(session, user.id, body)


@router.get("", response_model=list[ProjectOut])
async def list_projects(
    include_archived: bool = Query(False),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await project_service.list_projects(session, user.id, include_archived)


@router.get("/{project_id}", response_model=ProjectOut)
async def get_project(
    project_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await project_service.get_project(session, user.id, project_id)


@router.patch("/{project_id}", response_model=ProjectOut)
async def patch_project(
    project_id: str,
    body: ProjectPatch,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await project_service.patch_project(session, user.id, project_id, body)


@router.post("/{project_id}/archive", response_model=ProjectOut)
async def archive_project(
    project_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await project_service.archive_project(session, user.id, project_id)
