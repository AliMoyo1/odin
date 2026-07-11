from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import get_current_user
from app.models.models import Memory, User
from app.services import memory_service

router = APIRouter(prefix="/api/v1/memory", tags=["memory"])

_ACTIVE_CAP = 1000


class MemoryOut(BaseModel):
    id: str
    key: str | None
    value: str
    memory_type: str
    access_count: int
    created_at: datetime
    updated_at: datetime
    status: str
    conflict_with: str | None


class MemoryCreate(BaseModel):
    key: str
    value: str


class MemoryPatch(BaseModel):
    key: str | None = None
    value: str | None = None


class ReviewOut(BaseModel):
    active_count: int
    cap: int
    stale: list[MemoryOut]


def _to_out(m: Memory) -> MemoryOut:
    meta = m.extra_meta or {}
    return MemoryOut(
        id=m.id,
        key=m.key,
        value=m.value,
        memory_type=m.memory_type,
        access_count=m.access_count,
        created_at=m.created_at,
        updated_at=m.updated_at,
        status=meta.get("status", "active"),
        conflict_with=meta.get("conflict_with"),
    )


@router.get("", response_model=list[MemoryOut])
async def list_memories(
    status: str = Query("active"),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    if status not in {"active", "suggested", "archived"}:
        raise HTTPException(400, "status must be active, suggested, or archived")
    memories = await memory_service.list_memories(session, user.id, status=status)
    return [_to_out(m) for m in memories]


@router.post("", response_model=MemoryOut, status_code=201)
async def create_memory(
    body: MemoryCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    m = await memory_service.store_explicit(session, user.id, body.key, body.value)
    return _to_out(m)


@router.patch("/{memory_id}", response_model=MemoryOut)
async def update_memory(
    memory_id: str,
    body: MemoryPatch,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    from sqlalchemy import select
    from sqlalchemy.orm.attributes import flag_modified

    result = await session.execute(
        select(Memory).where(Memory.id == memory_id, Memory.user_id == user.id)
    )
    m = result.scalar_one_or_none()
    if m is None:
        raise HTTPException(404, "Memory not found")

    if body.key is not None:
        m.key = body.key
    if body.value is not None:
        from app.services.embeddings import embed_query, get_active_config
        config = await get_active_config(session)
        if config and body.value:
            m.embedding = await embed_query(body.value, config)
        m.value = body.value

    await session.commit()
    await session.refresh(m)
    return _to_out(m)


@router.delete("/{memory_id}", status_code=204)
async def delete_memory(
    memory_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    await memory_service.archive(session, memory_id, user.id)


@router.get("/suggestions", response_model=list[MemoryOut])
async def list_suggestions(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    memories = await memory_service.list_memories(session, user.id, status="suggested")
    return [_to_out(m) for m in memories]


@router.post("/suggestions/{memory_id}/approve", response_model=MemoryOut)
async def approve_suggestion(
    memory_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    m = await memory_service.approve_suggestion(session, memory_id, user.id)
    return _to_out(m)


@router.post("/suggestions/{memory_id}/reject", status_code=204)
async def reject_suggestion(
    memory_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    await memory_service.reject_suggestion(session, memory_id, user.id)


@router.get("/review", response_model=ReviewOut)
async def review_memories(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    stale = await memory_service.get_stale_memories(session, user.id)
    total = await memory_service.count_active(session, user.id)
    return ReviewOut(
        active_count=total,
        cap=_ACTIVE_CAP,
        stale=[_to_out(m) for m in stale],
    )
