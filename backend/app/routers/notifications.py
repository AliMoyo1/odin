from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import get_current_user
from app.models.models import User
from app.schemas.notifications import NotificationOut
from app.services import notification_service

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationOut])
async def list_notifications(
    unread_only: bool = Query(False),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await notification_service.list_notifications(session, user.id, unread_only)


@router.post("/{notification_id}/read", response_model=NotificationOut)
async def mark_read(
    notification_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await notification_service.mark_read(session, user.id, notification_id)


@router.post("/read-all")
async def mark_all_read(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    count = await notification_service.mark_all_read(session, user.id)
    return {"marked_read": count}
