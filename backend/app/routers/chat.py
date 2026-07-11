from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import get_current_user
from app.hermes import loop as hermes_loop
from app.models.models import User
from app.services import conversation_service

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])

_active_runs: dict[str, asyncio.Task] = {}


class ChatMessageRequest(BaseModel):
    conversation_id: str
    content: str
    interface_origin: str = "web"


@router.post("/message", status_code=202)
async def send_message(
    body: ChatMessageRequest,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    msg = await conversation_service.append_message(
        session,
        body.conversation_id,
        "user",
        body.content,
        metadata={"interface_origin": body.interface_origin},
    )

    task = asyncio.create_task(
        hermes_loop.run_turn(
            user_id=str(user.id),
            conversation_id=body.conversation_id,
            user_message_id=str(msg.id),
        )
    )
    _active_runs[body.conversation_id] = task

    def _cleanup(t: asyncio.Task) -> None:
        _active_runs.pop(body.conversation_id, None)

    task.add_done_callback(_cleanup)

    return {
        "message_id": str(msg.id),
        "status": "queued_for_generation",
        "metadata": {"conversation_id": body.conversation_id},
    }


@router.post("/stop/{conversation_id}", status_code=200)
async def stop_generation(
    conversation_id: str,
    user: User = Depends(get_current_user),
):
    task = _active_runs.pop(conversation_id, None)
    if task and not task.done():
        task.cancel()
        return {"status": "stopped"}
    return {"status": "not_running"}
