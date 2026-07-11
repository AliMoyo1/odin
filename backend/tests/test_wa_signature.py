"""
WhatsApp webhook signature and routing tests.
All run in WA_DRY_RUN mode; no real Meta calls are made.
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import time
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.main import app

_WA_URL = "/api/v1/integrations/whatsapp/webhook"
_TEST_SECRET = "test_app_secret_wa"
_TEST_VERIFY_TOKEN = "test_verify_token"
_TEST_ALLOWED = "15559990000"

# XFF IP unique to this test file
_WA_XFF = "5.6.7.130"


def _sign(secret: str, body: bytes) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def _text_payload(text: str, wamid: str, from_num: str) -> dict:
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "ENTRY",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {"display_phone_number": "1", "phone_number_id": "1"},
                            "messages": [
                                {
                                    "from": from_num,
                                    "id": wamid,
                                    "timestamp": str(int(time.time())),
                                    "type": "text",
                                    "text": {"body": text},
                                }
                            ],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }


def _status_payload(from_num: str) -> dict:
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "ENTRY",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "statuses": [
                                {
                                    "id": "wamid.status",
                                    "recipient_id": from_num,
                                    "status": "delivered",
                                    "timestamp": str(int(time.time())),
                                }
                            ],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }


@pytest_asyncio.fixture(autouse=True)
async def _patch_settings(monkeypatch):
    monkeypatch.setattr(settings, "WHATSAPP_APP_SECRET", _TEST_SECRET)
    monkeypatch.setattr(settings, "WHATSAPP_VERIFY_TOKEN", _TEST_VERIFY_TOKEN)
    monkeypatch.setattr(settings, "WHATSAPP_ALLOWED_NUMBER", _TEST_ALLOWED)
    monkeypatch.setattr(settings, "WA_DRY_RUN", True)

    # Reset dedup state between tests
    from app.routers.whatsapp import _dedup_deque, _dedup_set
    _dedup_deque.clear()
    _dedup_set.clear()


@pytest_asyncio.fixture
async def wa_client():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"X-Forwarded-For": _WA_XFF},
    ) as ac:
        yield ac


def _post_signed(body_dict: dict, secret: str = _TEST_SECRET) -> tuple[bytes, str]:
    body = json.dumps(body_dict).encode()
    sig = _sign(secret, body)
    return body, sig


@pytest.mark.asyncio
async def test_valid_signature_returns_200(wa_client):
    wamid = f"wamid.{uuid.uuid4().hex}"
    payload = _text_payload("hello", wamid, _TEST_ALLOWED)
    body, sig = _post_signed(payload)

    # Mock handle_inbound to do nothing
    import app.routers.whatsapp as wa_mod
    original = wa_mod._handle_inbound_safe

    async def _noop(msg, user_id):
        pass

    wa_mod._handle_inbound_safe = _noop
    wa_mod._user_id_cache = "fake-user-id"
    try:
        resp = await wa_client.post(
            _WA_URL,
            content=body,
            headers={"Content-Type": "application/json", "X-Hub-Signature-256": sig},
        )
    finally:
        wa_mod._handle_inbound_safe = original
        wa_mod._user_id_cache = None

    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_tampered_body_returns_401(wa_client):
    wamid = f"wamid.{uuid.uuid4().hex}"
    payload = _text_payload("hello", wamid, _TEST_ALLOWED)
    body, sig = _post_signed(payload)
    tampered = body[:-1] + b"!"  # corrupt last byte

    resp = await wa_client.post(
        _WA_URL,
        content=tampered,
        headers={"Content-Type": "application/json", "X-Hub-Signature-256": sig},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_missing_signature_header_returns_401(wa_client):
    payload = _text_payload("hello", "wamid.abc", _TEST_ALLOWED)
    body = json.dumps(payload).encode()

    resp = await wa_client.post(
        _WA_URL,
        content=body,
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_blank_app_secret_returns_503(wa_client, monkeypatch):
    monkeypatch.setattr(settings, "WHATSAPP_APP_SECRET", "")
    payload = _text_payload("hello", "wamid.abc", _TEST_ALLOWED)
    body = json.dumps(payload).encode()
    sig = _sign(_TEST_SECRET, body)

    resp = await wa_client.post(
        _WA_URL,
        content=body,
        headers={"Content-Type": "application/json", "X-Hub-Signature-256": sig},
    )
    assert resp.status_code == 503


@pytest.mark.asyncio
async def test_duplicate_wamid_processed_once(wa_client):
    wamid = f"wamid.{uuid.uuid4().hex}"
    payload = _text_payload("hello", wamid, _TEST_ALLOWED)
    body, sig = _post_signed(payload)

    call_count = 0

    import app.routers.whatsapp as wa_mod
    original = wa_mod._handle_inbound_safe
    wa_mod._user_id_cache = "fake-user-id"

    async def _counter(msg, user_id):
        nonlocal call_count
        call_count += 1

    wa_mod._handle_inbound_safe = _counter
    try:
        headers = {"Content-Type": "application/json", "X-Hub-Signature-256": sig}
        r1 = await wa_client.post(_WA_URL, content=body, headers=headers)
        r2 = await wa_client.post(_WA_URL, content=body, headers=headers)
    finally:
        wa_mod._handle_inbound_safe = original
        wa_mod._user_id_cache = None

    # Allow any background tasks to run
    await asyncio.sleep(0.05)

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert call_count == 1, f"Expected handler called once, got {call_count}"


@pytest.mark.asyncio
async def test_unbound_sender_acked_but_ignored(wa_client):
    wamid = f"wamid.{uuid.uuid4().hex}"
    payload = _text_payload("hello", wamid, "15550000000")  # not the allowed number
    body, sig = _post_signed(payload)

    call_count = 0
    import app.routers.whatsapp as wa_mod
    original = wa_mod._handle_inbound_safe
    wa_mod._user_id_cache = "fake-user-id"

    async def _counter(msg, user_id):
        nonlocal call_count
        call_count += 1

    wa_mod._handle_inbound_safe = _counter
    try:
        resp = await wa_client.post(
            _WA_URL,
            content=body,
            headers={"Content-Type": "application/json", "X-Hub-Signature-256": sig},
        )
    finally:
        wa_mod._handle_inbound_safe = original
        wa_mod._user_id_cache = None

    await asyncio.sleep(0.05)
    assert resp.status_code == 200
    assert call_count == 0, "Unbound sender should not trigger the handler"


@pytest.mark.asyncio
async def test_status_update_acked_200(wa_client):
    payload = _status_payload(_TEST_ALLOWED)
    body, sig = _post_signed(payload)

    resp = await wa_client.post(
        _WA_URL,
        content=body,
        headers={"Content-Type": "application/json", "X-Hub-Signature-256": sig},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_webhook_verification_get(wa_client):
    resp = await wa_client.get(
        _WA_URL,
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": _TEST_VERIFY_TOKEN,
            "hub.challenge": "challenge_abc_123",
        },
    )
    assert resp.status_code == 200
    assert resp.text == "challenge_abc_123"


@pytest.mark.asyncio
async def test_webhook_verification_wrong_token(wa_client):
    resp = await wa_client.get(
        _WA_URL,
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "wrong_token",
            "hub.challenge": "challenge_abc_123",
        },
    )
    assert resp.status_code == 403
