import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import redis.asyncio as aioredis
from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.models import Session as DbSession
from app.models.models import User
from app.security.jwt import create_access_token, create_preauth_token
from app.security.passwords import verify_password
from app.services.audit import log_event


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def _set_refresh_cookie(response, raw_token: str) -> None:
    response.set_cookie(
        key="odin_refresh",
        value=raw_token,
        httponly=True,
        secure=settings.ENVIRONMENT != "dev",
        samesite="strict",
        max_age=60 * 60 * 24 * 30,
        path="/api/v1/auth",
    )


def _clear_refresh_cookie(response) -> None:
    response.delete_cookie(key="odin_refresh", path="/api/v1/auth")


async def _create_session(session: AsyncSession, user_id: str) -> str:
    raw = secrets.token_urlsafe(48)
    db_session = DbSession(
        user_id=user_id,
        refresh_token_hash=_hash_token(raw),
        expires_at=datetime.now(timezone.utc) + timedelta(days=30),
    )
    session.add(db_session)
    return raw


async def login(
    session: AsyncSession,
    email: str,
    password: str,
    ip: str | None = None,
) -> dict:
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(password, user.password_hash):
        if user:
            await log_event(session, user.id, "login_failed", ip_address=ip)
        else:
            # Still write a log with a placeholder to prevent timing differences
            pass
        await session.commit()
        raise HTTPException(status_code=401, detail="Invalid credentials")

    await log_event(session, user.id, "login_success", ip_address=ip)

    if user.totp_enabled:
        await session.commit()
        return {"requires_totp": True, "pre_auth_token": create_preauth_token(user.id)}

    raw_refresh = await _create_session(session, user.id)
    await session.commit()
    return {
        "access_token": create_access_token(user.id),
        "token_type": "bearer",
        "expires_in": 900,
        "_raw_refresh": raw_refresh,
    }


async def rotate_refresh(session: AsyncSession, raw_token: str) -> dict:
    token_hash = _hash_token(raw_token)
    now = datetime.now(timezone.utc)

    result = await session.execute(
        select(DbSession).where(
            DbSession.refresh_token_hash == token_hash,
            DbSession.expires_at > now,
        )
    )
    db_session = result.scalar_one_or_none()
    if not db_session:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    user_id = db_session.user_id
    await session.delete(db_session)

    raw_refresh = await _create_session(session, user_id)
    await session.commit()
    return {
        "access_token": create_access_token(user_id),
        "token_type": "bearer",
        "expires_in": 900,
        "_raw_refresh": raw_refresh,
    }


async def logout(session: AsyncSession, raw_token: str) -> None:
    token_hash = _hash_token(raw_token)
    await session.execute(
        delete(DbSession).where(DbSession.refresh_token_hash == token_hash)
    )
    await session.commit()


async def invalidate_all_sessions(session: AsyncSession, user_id: str) -> None:
    await session.execute(delete(DbSession).where(DbSession.user_id == user_id))
    await session.commit()


# Password reset via Redis (no schema change)
async def create_reset_token(user_id: str) -> str:
    raw = secrets.token_urlsafe(48)
    token_hash = _hash_token(raw)
    r = aioredis.from_url(settings.REDIS_URL)
    try:
        await r.setex(f"reset:{token_hash}", 1800, user_id)
    finally:
        await r.aclose()
    return raw


async def consume_reset_token(raw_token: str) -> str | None:
    token_hash = _hash_token(raw_token)
    r = aioredis.from_url(settings.REDIS_URL)
    try:
        key = f"reset:{token_hash}"
        user_id = await r.getdel(key)
        return user_id.decode() if user_id else None
    finally:
        await r.aclose()
