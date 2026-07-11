import asyncio
import json

import pytest
import websockets
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.main import app
from tests.conftest import _WS_XFF

_WS_BASE = "ws://localhost:8000"


@pytest.fixture
async def authed_http(test_user):
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"X-Forwarded-For": _WS_XFF},
    ) as client:
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": test_user["email"], "password": test_user["password"]},
        )
        assert resp.status_code == 200, resp.text
        token = resp.json()["access_token"]
        client.headers["Authorization"] = f"Bearer {token}"
        yield client


async def _get_ticket(client: AsyncClient) -> str:
    resp = await client.post("/api/v1/ws-ticket")
    assert resp.status_code == 200, resp.text
    return resp.json()["ticket"]


def _check_4401_sync(url: str) -> None:
    """Open a WS connection in a fresh loop; assert server closes with 4401."""
    async def _inner():
        ws = await websockets.connect(url)
        try:
            await asyncio.wait_for(ws.wait_closed(), timeout=5)
        except asyncio.TimeoutError:
            await ws.close()
            raise AssertionError("Connection not closed within timeout")
        assert ws.close_code == 4401, f"Expected 4401, got {ws.close_code}"

    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(_inner())
    finally:
        loop.close()


def _first_connect_sync(ticket: str) -> None:
    """Open and immediately close a valid WS connection in a fresh loop."""
    async def _inner():
        async with websockets.connect(f"{_WS_BASE}/ws/events?ticket={ticket}"):
            pass

    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(_inner())
    finally:
        loop.close()


def _relay_event_sync(ticket: str, user_id: str, db_url: str) -> dict:
    """Connect WS, fire a notification, return the received event. Fresh loop.

    All resources (DB engine, Redis client) are created inside this loop so
    the events.py singleton (bound to the pytest session loop) is never touched.
    """
    result: dict = {}

    async def _inner():
        import redis.asyncio as aioredis

        engine = create_async_engine(db_url)
        sm = async_sessionmaker(engine, expire_on_commit=False)
        r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        try:
            async with websockets.connect(f"{_WS_BASE}/ws/events?ticket={ticket}") as ws:
                async with sm() as sess:
                    await sess.execute(
                        text(
                            "INSERT INTO notifications (user_id, title, body, category) "
                            "VALUES (:uid, :title, :body, :cat)"
                        ),
                        {"uid": user_id, "title": "Test notification", "body": "body text", "cat": "system"},
                    )
                    await sess.commit()
                await r.publish(
                    f"events:{user_id}",
                    json.dumps({"type": "notification.new", "data": {"title": "Test notification"}}),
                )
                raw = await asyncio.wait_for(ws.recv(), timeout=5)
                result["payload"] = json.loads(raw)
        finally:
            await engine.dispose()
            await r.aclose()

    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(_inner())
    finally:
        loop.close()

    return result["payload"]


async def test_valid_ticket_receives_event(authed_http, test_user):
    ticket = await _get_ticket(authed_http)

    loop = asyncio.get_running_loop()
    payload = await loop.run_in_executor(
        None,
        _relay_event_sync,
        ticket,
        test_user["id"],
        settings.DATABASE_URL,
    )

    assert payload["type"] == "notification.new"
    assert payload["data"]["title"] == "Test notification"


async def test_reused_ticket_gets_4401(authed_http):
    ticket = await _get_ticket(authed_http)

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _first_connect_sync, ticket)
    await loop.run_in_executor(
        None, _check_4401_sync, f"{_WS_BASE}/ws/events?ticket={ticket}"
    )


async def test_expired_ticket_gets_4401(authed_http, test_user):
    engine = create_async_engine(settings.DATABASE_URL)
    sm = async_sessionmaker(engine, expire_on_commit=False)
    async with sm() as session:
        result = await session.execute(
            text(
                "INSERT INTO ws_tickets (user_id, used, expires_at) "
                "VALUES (:uid, FALSE, NOW() - INTERVAL '1 minute') "
                "RETURNING id"
            ),
            {"uid": test_user["id"]},
        )
        row = result.fetchone()
        await session.commit()
        expired_id = str(row.id)
    await engine.dispose()

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(
        None, _check_4401_sync, f"{_WS_BASE}/ws/events?ticket={expired_id}"
    )
