from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt

from app.config import settings

_ALGORITHM = "RS256"
_ACCESS_EXPIRE_MINUTES = 15
_PREAUTH_EXPIRE_MINUTES = 5


def _private_key() -> bytes:
    return Path(settings.JWT_PRIVATE_KEY_PATH).read_bytes()


def _public_key() -> bytes:
    return Path(settings.JWT_PUBLIC_KEY_PATH).read_bytes()


def create_access_token(user_id: str, scope: str = "access") -> str:
    now = datetime.now(timezone.utc)
    minutes = _PREAUTH_EXPIRE_MINUTES if scope == "preauth" else _ACCESS_EXPIRE_MINUTES
    payload = {
        "sub": user_id,
        "scope": scope,
        "iat": now,
        "exp": now + timedelta(minutes=minutes),
    }
    return jwt.encode(payload, _private_key(), algorithm=_ALGORITHM)


def create_preauth_token(user_id: str) -> str:
    return create_access_token(user_id, scope="preauth")


def decode_token(token: str, required_scope: str = "access") -> dict:
    payload = jwt.decode(token, _public_key(), algorithms=[_ALGORITHM])
    if payload.get("scope") != required_scope:
        raise jwt.InvalidTokenError(f"Expected scope '{required_scope}', got '{payload.get('scope')}'")
    return payload
