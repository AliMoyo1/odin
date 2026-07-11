from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import ActivityLog


async def log_event(
    session: AsyncSession,
    user_id: str,
    action: str,
    *,
    resource_type: str | None = None,
    resource_id: str | None = None,
    ip_address: str | None = None,
    source: str | None = None,
    metadata: dict | None = None,
) -> None:
    meta = dict(metadata or {})
    if source:
        meta["source"] = source
    entry = ActivityLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=ip_address,
        extra_meta=meta or None,
    )
    session.add(entry)
    # Caller commits
