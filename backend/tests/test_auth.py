import pyotp
import pytest
import redis.asyncio as aioredis

from app.config import settings
from app.security.totp import decrypt_secret


# --- Login ---

async def test_login_success(client, test_user):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": test_user["email"], "password": test_user["password"]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    cookie = resp.cookies.get("odin_refresh")
    assert cookie is not None


async def test_login_wrong_password(client, test_user):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": test_user["email"], "password": "wrongpassword"},
    )
    assert resp.status_code == 401


async def test_login_unknown_email(client):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@odin.local", "password": "anything"},
    )
    assert resp.status_code == 401


# --- Refresh rotation ---

async def test_refresh_rotates(client, test_user):
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": test_user["email"], "password": test_user["password"]},
    )
    assert login.status_code == 200
    old_cookie = login.cookies["odin_refresh"]

    # First refresh succeeds
    r1 = await client.post("/api/v1/auth/refresh", cookies={"odin_refresh": old_cookie})
    assert r1.status_code == 200
    new_cookie = r1.cookies["odin_refresh"]
    assert new_cookie != old_cookie

    # Old cookie is now invalid
    r2 = await client.post("/api/v1/auth/refresh", cookies={"odin_refresh": old_cookie})
    assert r2.status_code == 401


# --- Preauth token rejected on normal route ---

async def test_preauth_token_rejected(client, test_user):
    from app.security.jwt import create_preauth_token
    preauth = create_preauth_token(test_user["id"])
    resp = await client.post(
        "/api/v1/ws-ticket",
        headers={"Authorization": f"Bearer {preauth}"},
    )
    assert resp.status_code == 401


# --- WS ticket ---

async def test_ws_ticket_issued(authed_client):
    resp = await authed_client.post("/api/v1/ws-ticket")
    assert resp.status_code == 200
    data = resp.json()
    assert "ticket" in data
    assert data["expires_in_seconds"] == 30


# --- Rate limiting ---

async def test_rate_limit(client, test_user):
    # Use an IP isolated from other tests
    rl_xff = "5.6.7.201"
    headers = {"X-Forwarded-For": rl_xff}

    r = aioredis.from_url(settings.REDIS_URL)
    await r.delete(f"rl:auth:{rl_xff}")
    await r.aclose()

    for _ in range(5):
        await client.post(
            "/api/v1/auth/login",
            json={"email": test_user["email"], "password": "wrong"},
            headers=headers,
        )

    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": test_user["email"], "password": "wrong"},
        headers=headers,
    )
    assert resp.status_code == 429

    r = aioredis.from_url(settings.REDIS_URL)
    await r.delete(f"rl:auth:{rl_xff}")
    await r.aclose()


# --- TOTP ---

async def test_totp_lockout(authed_client, test_user):
    # Setup TOTP
    setup = await authed_client.post("/api/v1/auth/totp/setup")
    assert setup.status_code == 200

    # Enable TOTP with a real code
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from app.models.models import User

    engine = create_async_engine(settings.DATABASE_URL)
    sm = async_sessionmaker(engine, expire_on_commit=False)
    async with sm() as s:
        result = await s.execute(select(User).where(User.id == test_user["id"]))
        user = result.scalar_one()
        secret = decrypt_secret(user.totp_secret_enc)

    valid_code = pyotp.TOTP(secret).now()
    enable = await authed_client.post("/api/v1/auth/totp/enable", json={"code": valid_code})
    assert enable.status_code == 200

    # Login returns requires_totp
    login = await authed_client.post(
        "/api/v1/auth/login",
        json={"email": test_user["email"], "password": test_user["password"]},
    )
    # authed_client already has auth; use a fresh client for login
    await engine.dispose()

    # Get preauth token via a plain client
    from httpx import ASGITransport, AsyncClient
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        login2 = await ac.post(
            "/api/v1/auth/login",
            json={"email": test_user["email"], "password": test_user["password"]},
        )
        assert login2.status_code == 200
        data = login2.json()
        assert data.get("requires_totp") is True
        preauth = data["pre_auth_token"]

        # 5 wrong codes trigger lockout
        for _ in range(5):
            r = await ac.post(
                "/api/v1/auth/totp/verify",
                json={"code": "000000"},
                headers={"Authorization": f"Bearer {preauth}"},
            )
            assert r.status_code == 401

        # 6th attempt (even with correct code) returns 423
        correct = pyotp.TOTP(secret).now()
        r = await ac.post(
            "/api/v1/auth/totp/verify",
            json={"code": correct},
            headers={"Authorization": f"Bearer {preauth}"},
        )
        assert r.status_code == 423

    # Disable TOTP for subsequent tests: reset the user directly
    engine2 = create_async_engine(settings.DATABASE_URL)
    sm2 = async_sessionmaker(engine2, expire_on_commit=False)
    async with sm2() as s:
        result = await s.execute(select(User).where(User.id == test_user["id"]))
        user = result.scalar_one()
        user.totp_enabled = False
        user.totp_locked_until = None
        user.totp_fail_count = 0
        await s.commit()
    await engine2.dispose()
