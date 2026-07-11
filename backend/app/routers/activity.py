from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import get_current_user
from app.models.models import ActivityLog, User
from app.schemas.notifications import ActivityOut

router = APIRouter(prefix="/api/v1/activity", tags=["activity"])


@router.get("", response_model=list[ActivityOut])
async def list_activity(
    limit: int = Query(50, ge=1, le=200),
    event_type: str | None = Query(None),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    q = select(ActivityLog).where(ActivityLog.user_id == user.id)
    if event_type:
        q = q.where(ActivityLog.action == event_type)
    q = q.order_by(ActivityLog.created_at.desc()).limit(limit)
    result = await session.execute(q)
    return list(result.scalars().all())
