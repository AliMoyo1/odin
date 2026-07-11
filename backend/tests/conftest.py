import pytest
import pytest_asyncio
import redis.asyncio as aioredis
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.main import app
from app.models.models import Session as DbSession
from app.models.models import User
from app.security.passwords import hash_password

TEST_EMAIL = "test_auth@odin.local"
TEST_PASSWORD = "TestPass123!"

# Unique XFF IPs: isolated from each other and from the rate_limit test (5.6.7.201)
_TEST_XFF = "5.6.7.100"       # used by the generic `client` fixture
_AUTHED_XFF = "5.6.7.102"    # used by `authed_client` (auth tests)
_TOTP_XFF = "5.6.7.104"      # used inside test_totp_lockout
_TASKS_XFF = "5.6.7.106"     # used by test_tasks.py ac fixture
_WS_XFF = "5.6.7.108"        # used by test_ws.py authed_http fixture
_GATE_XFF = "5.6.7.120"      # used by test_gate.py gate_client fixture

_ALL_TEST_IPS = [_TEST_XFF, _AUTHED_XFF, _TOTP_XFF, _TASKS_XFF, _WS_XFF, _GATE_XFF]


@pytest_asyncio.fixture(scope="session")
async def test_user():
    engine = create_async_engine(settings.DATABASE_URL)
    sm = async_sessionmaker(engine, expire_on_commit=False)

    async with sm() as session:
        await session.execute(delete(User).where(User.email == TEST_EMAIL))
        await session.commit()
        user = User(email=TEST_EMAIL, password_hash=hash_password(TEST_PASSWORD))
        session.add(user)
        await session.commit()
        await session.refresh(user)
        uid = user.id

    # Clear any leftover rate-limit state for all test IPs
    r = aioredis.from_url(settings.REDIS_URL)
    for ip in _ALL_TEST_IPS:
        await r.delete(f"rl:auth:{ip}")
    await r.aclose()

    yield {"id": uid, "email": TEST_EMAIL, "password": TEST_PASSWORD}

    async with sm() as session:
        await session.execute(delete(User).where(User.email == TEST_EMAIL))
        await session.commit()

    await engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def _reset_rate_limits():
    r = aioredis.from_url(settings.REDIS_URL)
    for ip in _ALL_TEST_IPS:
        await r.delete(f"rl:auth:{ip}")
    await r.aclose()


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"X-Forwarded-For": _TEST_XFF},
    ) as ac:
        yield ac


@pytest_asyncio.fixture
async def authed_client(test_user):
    """Client with a valid access token already set."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"X-Forwarded-For": _AUTHED_XFF},
    ) as ac:
        resp = await ac.post(
            "/api/v1/auth/login",
            json={"email": test_user["email"], "password": test_user["password"]},
        )
        assert resp.status_code == 200, resp.text
        token = resp.json()["access_token"]
        ac.headers["Authorization"] = f"Bearer {token}"
        yield ac
