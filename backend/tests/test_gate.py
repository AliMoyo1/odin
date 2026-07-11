from __future__ import annotations

import json

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.hermes import gate as _gate
from app.hermes.types import ToolCall
from app.main import app
from tests.conftest import _GATE_XFF


@pytest.fixture
async def gate_client(test_user):
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"X-Forwarded-For": _GATE_XFF},
    ) as client:
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": test_user["email"], "password": test_user["password"]},
        )
        assert resp.status_code == 200, resp.text
        token = resp.json()["access_token"]
        client.headers["Authorization"] = f"Bearer {token}"
        yield client


@pytest.fixture(autouse=True)
async def _cleanup_approvals(test_user):
    engine = create_async_engine(settings.DATABASE_URL)
    sm = async_sessionmaker(engine, expire_on_commit=False)
    async with sm() as s:
        await s.execute(
            text("DELETE FROM tool_approvals WHERE user_id = :uid"), {"uid": test_user["id"]}
        )
        await s.commit()
    await engine.dispose()
    yield


async def test_gate_locked_creates_redis_key(test_user):
    call = ToolCall(id="tc1", name="write_file", arguments={"path": "test.txt", "content": "hi"})
    approval_id, ttl = await _gate.create_gate(
        conversation_id="conv-1",
        user_id=test_user["id"],
        project_id=None,
        call=call,
        provider_messages_snapshot=[],
    )
    assert approval_id
    assert ttl == 600
    exists = await _gate.gate_exists(approval_id)
    assert exists


async def test_approve_executes_and_consumes_key(gate_client, test_user):
    call = ToolCall(id="tc2", name="write_file", arguments={"path": "gate_test.txt", "content": "approved"})
    approval_id, _ = await _gate.create_gate(
        conversation_id="conv-2",
        user_id=test_user["id"],
        project_id=None,
        call=call,
        provider_messages_snapshot=[],
    )

    resp = await gate_client.post(f"/api/v1/approvals/{approval_id}/approve", json={"remember": False})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "approved"

    # Key should be consumed (deleted)
    exists = await _gate.gate_exists(approval_id)
    assert not exists


async def test_deny_consumes_key(gate_client, test_user):
    call = ToolCall(id="tc3", name="write_file", arguments={"path": "deny_test.txt", "content": "nope"})
    approval_id, _ = await _gate.create_gate(
        conversation_id="conv-3",
        user_id=test_user["id"],
        project_id=None,
        call=call,
        provider_messages_snapshot=[],
    )

    resp = await gate_client.post(f"/api/v1/approvals/{approval_id}/deny")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "denied"

    exists = await _gate.gate_exists(approval_id)
    assert not exists


async def test_expired_approval_returns_410(gate_client):
    fake_id = "00000000-0000-0000-0000-000000000001"
    resp = await gate_client.post(f"/api/v1/approvals/{fake_id}/approve", json={})
    assert resp.status_code == 410


async def test_remember_writes_tool_approvals(gate_client, test_user):
    call = ToolCall(id="tc4", name="write_file", arguments={"path": "remember.txt", "content": "memo"})
    approval_id, _ = await _gate.create_gate(
        conversation_id="conv-4",
        user_id=test_user["id"],
        project_id=None,
        call=call,
        provider_messages_snapshot=[],
    )

    resp = await gate_client.post(f"/api/v1/approvals/{approval_id}/approve", json={"remember": True})
    assert resp.status_code == 200, resp.text

    engine = create_async_engine(settings.DATABASE_URL)
    sm = async_sessionmaker(engine, expire_on_commit=False)
    async with sm() as s:
        result = await s.execute(
            text("SELECT auto_approve FROM tool_approvals WHERE user_id = :uid AND tool_name = 'write_file'"),
            {"uid": test_user["id"]},
        )
        row = result.fetchone()
    await engine.dispose()
    assert row is not None
    assert row.auto_approve is True


async def test_second_call_skips_gate_after_remember(gate_client, test_user):
    # Insert a tool_approvals row for this user+tool
    engine = create_async_engine(settings.DATABASE_URL)
    sm = async_sessionmaker(engine, expire_on_commit=False)
    async with sm() as s:
        await s.execute(
            text("""
                INSERT INTO tool_approvals (user_id, tool_name, project_id, auto_approve)
                VALUES (:uid, 'write_file', NULL, TRUE)
                ON CONFLICT ON CONSTRAINT uq_tool_approvals DO UPDATE SET auto_approve = TRUE
            """),
            {"uid": test_user["id"]},
        )
        await s.commit()
    await engine.dispose()

    from app.hermes.loop import _has_auto_approval
    auto = await _has_auto_approval(test_user["id"], "write_file", None)
    assert auto is True
