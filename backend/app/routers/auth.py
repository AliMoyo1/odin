from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import get_current_user, get_preauth_user
from app.models.models import User, WsTicket
from app.security.ratelimit import check_auth_rate_limit, _resolve_ip
from app.security.totp import (
    decrypt_secret,
    encrypt_secret,
    generate_secret,
    provisioning_uri,
    verify_code,
)
from app.services import auth_service
from app.services.audit import log_event

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
ws_router = APIRouter(prefix="/api/v1", tags=["ws"])

logger = structlog.get_logger(service="auth")

TOTP_MAX_FAILURES = 5
TOTP_LOCKOUT_MINUTES = 15


# --- Models ---

class LoginRequest(BaseModel):
    email: str
    password: str


class TotpVerifyRequest(BaseModel):
    code: str


class TotpEnableRequest(BaseModel):
    code: str


class ForgotRequest(BaseModel):
    email: str


class ResetRequest(BaseModel):
    token: str
    new_password: str


# --- Helpers ---

def _set_refresh_cookie(response: Response, raw: str) -> None:
    from app.config import settings
    response.set_cookie(
        key="odin_refresh",
        value=raw,
        httponly=True,
        secure=settings.ENVIRONMENT != "dev",
        samesite="strict",
        max_age=60 * 60 * 24 * 30,
        path="/api/v1/auth",
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key="odin_refresh", path="/api/v1/auth")


def _token_response(result: dict, response: Response) -> dict:
    _set_refresh_cookie(response, result.pop("_raw_refresh"))
    return result


# --- Login ---

@router.post("/login")
async def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
    _: None = Depends(check_auth_rate_limit),
):
    ip = _resolve_ip(request)
    result = await auth_service.login(session, body.email, body.password, ip=ip)
    if result.get("requires_totp"):
        return result
    return _token_response(result, response)


# --- Refresh ---

@router.post("/refresh")
async def refresh(
    response: Response,
    odin_refresh: str | None = Cookie(default=None),
    session: AsyncSession = Depends(get_session),
):
    if not odin_refresh:
        raise HTTPException(status_code=401, detail="No refresh token")
    result = await auth_service.rotate_refresh(session, odin_refresh)
    return _token_response(result, response)


# --- Logout ---

@router.post("/logout")
async def logout(
    response: Response,
    odin_refresh: str | None = Cookie(default=None),
    session: AsyncSession = Depends(get_session),
):
    if odin_refresh:
        await auth_service.logout(session, odin_refresh)
    _clear_refresh_cookie(response)
    return {"ok": True}


# --- TOTP setup ---

@router.post("/totp/setup")
async def totp_setup(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    secret = generate_secret()
    user.totp_secret_enc = encrypt_secret(secret)
    await session.commit()
    uri = provisioning_uri(secret, user.email)
    return {"provisioning_uri": uri}


@router.post("/totp/enable")
async def totp_enable(
    body: TotpEnableRequest,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    if not user.totp_secret_enc:
        raise HTTPException(400, "Run /totp/setup first")
    secret = decrypt_secret(user.totp_secret_enc)
    if not verify_code(secret, body.code):
        raise HTTPException(400, "Invalid TOTP code")
    user.totp_enabled = True
    await session.commit()
    return {"ok": True, "two_factor_enabled": True}


# --- TOTP verify (preauth flow) ---

@router.post("/totp/verify")
async def totp_verify(
    body: TotpVerifyRequest,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_preauth_user),
):
    now = datetime.now(timezone.utc)

    # Lockout check FIRST, before touching the submitted code
    if user.totp_locked_until and user.totp_locked_until > now:
        remaining = int((user.totp_locked_until - now).total_seconds())
        raise HTTPException(
            status_code=423,
            detail=f"Account locked. Try again in {remaining} seconds.",
        )

    if not user.totp_secret_enc:
        raise HTTPException(400, "TOTP not configured")

    secret = decrypt_secret(user.totp_secret_enc)
    success = verify_code(secret, body.code)

    if not success:
        user.totp_fail_count = (user.totp_fail_count or 0) + 1
        if user.totp_fail_count >= TOTP_MAX_FAILURES:
            from datetime import timedelta
            user.totp_locked_until = now + timedelta(minutes=TOTP_LOCKOUT_MINUTES)
            user.totp_fail_count = 0
            await log_event(
                session, user.id, "totp_lockout",
                ip_address=_resolve_ip(request),
            )
        await session.commit()
        raise HTTPException(status_code=401, detail="Invalid TOTP code")

    user.totp_fail_count = 0
    user.totp_locked_until = None
    raw_refresh = await auth_service._create_session(session, user.id)
    await log_event(session, user.id, "login_success", ip_address=_resolve_ip(request))
    await session.commit()

    from app.security.jwt import create_access_token
    result = {
        "access_token": create_access_token(user.id),
        "token_type": "bearer",
        "expires_in": 900,
    }
    _set_refresh_cookie(response, raw_refresh)
    return result


# --- Password reset ---

@router.post("/forgot", status_code=202)
async def forgot_password(
    body: ForgotRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    _: None = Depends(check_auth_rate_limit),
):
    result = await session.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if user:
        raw = await auth_service.create_reset_token(user.id)
        from app.config import settings
        reset_url = f"{settings.CORS_ALLOWED_ORIGIN}/reset?token={raw}"
        if settings.SMTP_HOST:
            # Send email (aiosmtplib)
            try:
                import aiosmtplib
                from email.message import EmailMessage
                msg = EmailMessage()
                msg["From"] = settings.SMTP_FROM
                msg["To"] = user.email
                msg["Subject"] = "ODIN password reset"
                msg.set_content(f"Reset your password: {reset_url}\n\nExpires in 30 minutes.")
                await aiosmtplib.send(
                    msg,
                    hostname=settings.SMTP_HOST,
                    port=settings.SMTP_PORT,
                    username=settings.SMTP_USER or None,
                    password=settings.SMTP_PASSWORD or None,
                )
            except Exception as exc:
                logger.warning("smtp_send_failed", error=str(exc))
        else:
            logger.info("password_reset_url", url=reset_url)
    return {"detail": "If that email exists, a reset link has been sent."}


@router.post("/reset")
async def reset_password(
    body: ResetRequest,
    session: AsyncSession = Depends(get_session),
):
    if len(body.new_password.encode("utf-8")) > 72:
        raise HTTPException(400, "Password must be 72 bytes or fewer")
    if len(body.new_password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters")

    user_id = await auth_service.consume_reset_token(body.token)
    if not user_id:
        raise HTTPException(400, "Invalid or expired reset token")

    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(400, "User not found")

    from app.security.passwords import hash_password
    user.password_hash = hash_password(body.new_password)
    await auth_service.invalidate_all_sessions(session, user.id)
    await log_event(session, user.id, "password_reset")
    await session.commit()
    return {"ok": True}


# --- WS ticket ---

@ws_router.post("/ws-ticket")
async def issue_ws_ticket(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    from datetime import timedelta
    ticket = WsTicket(
        user_id=user.id,
        expires_at=datetime.now(timezone.utc) + timedelta(seconds=30),
    )
    session.add(ticket)
    await session.commit()
    await session.refresh(ticket)
    return {"ticket": ticket.id, "expires_in_seconds": 30}
