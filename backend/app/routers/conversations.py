from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import get_current_user
from app.models.models import User
from app.schemas.conversations import (
    ConversationCreate,
    ConversationOut,
    ConversationPatch,
    MessageCreate,
    MessageOut,
    MessageSearchResult,
)
from app.services import conversation_service

router = APIRouter(prefix="/api/v1/conversations", tags=["conversations"])
search_router = APIRouter(prefix="/api/v1/search", tags=["search"])


@router.post("", response_model=ConversationOut, status_code=201)
async def create_conversation(
    body: ConversationCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await conversation_service.create_conversation(session, user.id, body)


@router.get("", response_model=list[ConversationOut])
async def list_conversations(
    project_id: str | None = Query(None),
    archived: bool = Query(False),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await conversation_service.list_conversations(session, user.id, project_id, archived)


@router.get("/{conv_id}", response_model=ConversationOut)
async def get_conversation(
    conv_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await conversation_service.get_conversation(session, user.id, conv_id)


@router.patch("/{conv_id}", response_model=ConversationOut)
async def patch_conversation(
    conv_id: str,
    body: ConversationPatch,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await conversation_service.patch_conversation(session, user.id, conv_id, body)


@router.post("/{conv_id}/messages", response_model=MessageOut, status_code=201)
async def add_message(
    conv_id: str,
    body: MessageCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    await conversation_service.get_conversation(session, user.id, conv_id)
    return await conversation_service.append_message(
        session, conv_id, body.role, body.content, token_count=body.token_count
    )


@router.get("/{conv_id}/messages", response_model=list[MessageOut])
async def get_messages(
    conv_id: str,
    limit: int = Query(50, ge=1, le=200),
    before: str | None = Query(None),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await conversation_service.get_messages(session, user.id, conv_id, limit, before)


@search_router.get("/messages", response_model=list[MessageSearchResult])
async def search_messages(
    q: str = Query(..., min_length=1),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    rows = await conversation_service.search_messages(session, user.id, q)
    return [MessageSearchResult(**r) for r in rows]
