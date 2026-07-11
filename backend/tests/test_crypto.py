"""Tests for AES-256-GCM crypto primitive."""
from __future__ import annotations

import base64

import pytest


@pytest.fixture(autouse=True)
def _patch_key(monkeypatch):
    import base64
    import os
    # 32 random bytes, base64-encoded - valid AES-256 key
    key = base64.b64encode(os.urandom(32)).decode()
    monkeypatch.setattr("app.config.settings.ENCRYPTION_KEY", key)


def test_round_trip():
    from app.services.crypto import decrypt, encrypt
    plaintext = "Hello, secret world!"
    blob = encrypt(plaintext)
    assert isinstance(blob, str)
    assert decrypt(blob) == plaintext


def test_round_trip_empty_string():
    from app.services.crypto import decrypt, encrypt
    blob = encrypt("")
    assert decrypt(blob) == ""


def test_round_trip_unicode():
    from app.services.crypto import decrypt, encrypt
    plaintext = "ODIN: 密码 Passwort тайна"
    assert decrypt(encrypt(plaintext)) == plaintext


def test_tampered_blob_raises():
    from cryptography.exceptions import InvalidTag
    from app.services.crypto import decrypt, encrypt

    blob = encrypt("sensitive data")
    raw = base64.b64decode(blob)
    # Flip one byte in the ciphertext (after the 12-byte nonce)
    tampered_raw = raw[:13] + bytes([raw[13] ^ 0xFF]) + raw[14:]
    tampered = base64.b64encode(tampered_raw).decode()

    with pytest.raises(InvalidTag):
        decrypt(tampered)


def test_nonce_differs_across_encryptions():
    from app.services.crypto import encrypt

    blob1 = encrypt("same plaintext")
    blob2 = encrypt("same plaintext")

    # Blobs differ because nonces are random
    assert blob1 != blob2

    # But nonces themselves (first 12 bytes) differ
    nonce1 = base64.b64decode(blob1)[:12]
    nonce2 = base64.b64decode(blob2)[:12]
    assert nonce1 != nonce2
