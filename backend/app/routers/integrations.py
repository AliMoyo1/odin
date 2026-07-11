from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import get_current_user
from app.models.models import User
from app.services import integration_service

router = APIRouter(prefix="/api/v1/integrations", tags=["integrations"])

_ALLOWED = integration_service.KNOWN_SERVICES


class CredBody(BaseModel):
    credentials: dict


@router.get("")
async def list_integrations(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await integration_service.list_integrations(session, user.id)


@router.post("/{service}", status_code=204)
async def set_integration(
    service: str,
    body: CredBody,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    if service not in _ALLOWED:
        raise HTTPException(400, f"Unknown service. Allowed: {sorted(_ALLOWED)}")
    await integration_service.set_credentials(session, user.id, service, body.credentials)


@router.delete("/{service}", status_code=204)
async def delete_integration(
    service: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    if service not in _ALLOWED:
        raise HTTPException(400, f"Unknown service. Allowed: {sorted(_ALLOWED)}")
    await integration_service.delete_integration(session, user.id, service)
