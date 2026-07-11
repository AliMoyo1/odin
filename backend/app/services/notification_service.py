from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Notification
from app.services.events import publish


async def notify(
    session: AsyncSession,
    user_id: str,
    title: str,
    body: str | None,
    category: str,
) -> Notification:
    n = Notification(user_id=user_id, title=title, body=body, category=category)
    session.add(n)
    await session.commit()
    await session.refresh(n)
    await publish(
        f"events:{user_id}",
        "notification.new",
        {"id": str(n.id), "title": title, "body": body, "category": category},
    )
    return n


async def list_notifications(
    session: AsyncSession, user_id: str, unread_only: bool = False
) -> list[Notification]:
    q = select(Notification).where(Notification.user_id == user_id)
    if unread_only:
        q = q.where(Notification.read == False)
    q = q.order_by(Notification.created_at.desc())
    result = await session.execute(q)
    return list(result.scalars().all())


async def mark_read(session: AsyncSession, user_id: str, notification_id: str) -> Notification:
    result = await session.execute(
        select(Notification).where(
            Notification.id == notification_id, Notification.user_id == user_id
        )
    )
    n = result.scalar_one_or_none()
    if not n:
        raise HTTPException(404, "Notification not found")
    n.read = True
    await session.commit()
    await session.refresh(n)
    return n


async def mark_all_read(session: AsyncSession, user_id: str) -> int:
    result = await session.execute(
        select(Notification).where(
            Notification.user_id == user_id, Notification.read == False
        )
    )
    notifications = result.scalars().all()
    for n in notifications:
        n.read = True
    await session.commit()
    return len(notifications)


async def count_unread(session: AsyncSession, user_id: str) -> int:
    result = await session.execute(
        select(Notification).where(
            Notification.user_id == user_id, Notification.read == False
        )
    )
    return len(result.scalars().all())
