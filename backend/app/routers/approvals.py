from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import get_current_user
from app.hermes import gate as _gate
from app.hermes import loop as hermes_loop
from app.hermes.tools.registry import registry as tool_registry
from app.models.models import User

router = APIRouter(prefix="/api/v1/approvals", tags=["approvals"])


class ApproveBody(BaseModel):
    remember: bool = False


@router.post("/{approval_id}/approve", status_code=200)
async def approve(
    approval_id: str,
    body: ApproveBody,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    data = await _gate.consume_gate(approval_id)
    if data is None:
        raise HTTPException(status_code=410, detail="Approval expired or already consumed")
    if data["user_id"] != str(user.id):
        raise HTTPException(status_code=403, detail="Not your approval")

    tool_name = data["tool_call"]["name"]
    project_id = data.get("project_id")

    # Execute the tool
    from app.hermes.types import ToolCall
    call = ToolCall(
        id=data["tool_call"]["id"],
        name=tool_name,
        arguments=data["tool_call"]["arguments"],
    )
    result_text = await tool_registry.dispatch(call, db_session=session, user_id=str(user.id))

    if body.remember:
        await session.execute(
            text("""
                INSERT INTO tool_approvals (user_id, tool_name, project_id, auto_approve)
                VALUES (:uid, :tn, :pid, TRUE)
                ON CONFLICT ON CONSTRAINT uq_tool_approvals DO UPDATE SET auto_approve = TRUE, updated_at = now()
            """),
            {"uid": str(user.id), "tn": tool_name, "pid": project_id},
        )
        await session.commit()

    asyncio.create_task(hermes_loop.resume_from_gate(data, result_text))

    return {"status": "approved", "tool": tool_name, "remember": body.remember}


@router.post("/{approval_id}/deny", status_code=200)
async def deny(
    approval_id: str,
    user: User = Depends(get_current_user),
):
    data = await _gate.consume_gate(approval_id)
    if data is None:
        raise HTTPException(status_code=410, detail="Approval expired or already consumed")
    if data["user_id"] != str(user.id):
        raise HTTPException(status_code=403, detail="Not your approval")

    asyncio.create_task(
        hermes_loop.resume_from_gate(data, json.dumps({"ok": False, "message": "denied by user"}))
    )

    return {"status": "denied", "tool": data["tool_call"]["name"]}
