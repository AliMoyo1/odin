#!/usr/bin/env python3
"""
WhatsApp webhook simulator for local testing.

Usage:
  python scripts/simulate_wa.py --text "hello Hermes"
  python scripts/simulate_wa.py --text "hi" --wamid custom-id-123
  python scripts/simulate_wa.py --text "hi" --from-number 15550000000
  python scripts/simulate_wa.py --text "hi" --tamper
  python scripts/simulate_wa.py --audio-id <media_id>
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import sys
import time
import uuid

import httpx


def _build_text_payload(text: str, wamid: str, from_number: str) -> dict:
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "ENTRY_ID",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "15550000001",
                                "phone_number_id": "PHONE_NUMBER_ID",
                            },
                            "messages": [
                                {
                                    "from": from_number,
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


def _build_audio_payload(media_id: str, wamid: str, from_number: str) -> dict:
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "ENTRY_ID",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "15550000001",
                                "phone_number_id": "PHONE_NUMBER_ID",
                            },
                            "messages": [
                                {
                                    "from": from_number,
                                    "id": wamid,
                                    "timestamp": str(int(time.time())),
                                    "type": "audio",
                                    "audio": {
                                        "id": media_id,
                                        "mime_type": "audio/ogg; codecs=opus",
                                        "sha256": "abc123",
                                        "voice": True,
                                        "duration": 5,
                                    },
                                }
                            ],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }


def _build_status_payload(from_number: str) -> dict:
    """Delivery receipt - no messages key."""
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "ENTRY_ID",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "statuses": [
                                {
                                    "id": "wamid.status001",
                                    "recipient_id": from_number,
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


def _sign(secret: str, body: bytes) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulate a WhatsApp webhook POST")
    parser.add_argument("--text", help="Text message body")
    parser.add_argument("--audio-id", help="Media ID for an audio message")
    parser.add_argument("--status", action="store_true", help="Send a delivery receipt (no messages)")
    parser.add_argument("--wamid", default=f"wamid.{uuid.uuid4().hex}", help="Message ID (default: random)")
    parser.add_argument("--from-number", default=None, help="Sender phone number (digits only, no plus)")
    parser.add_argument("--tamper", action="store_true", help="Corrupt the body after signing (should get 401)")
    parser.add_argument("--url", default="http://localhost:8000/api/v1/integrations/whatsapp/webhook")
    args = parser.parse_args()

    # Load secret from .env
    secret = os.getenv("WHATSAPP_APP_SECRET", "")
    allowed = os.getenv("WHATSAPP_ALLOWED_NUMBER", "15559990000")
    if not secret:
        # Try reading .env directly
        env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
        if os.path.exists(env_path):
            for line in open(env_path):
                line = line.strip()
                if line.startswith("WHATSAPP_APP_SECRET="):
                    secret = line.split("=", 1)[1].strip().strip('"').strip("'")
                if line.startswith("WHATSAPP_ALLOWED_NUMBER="):
                    allowed = line.split("=", 1)[1].strip().strip('"').strip("'")

    if not secret:
        print("ERROR: WHATSAPP_APP_SECRET not set in environment or .env")
        sys.exit(1)

    from_number = args.from_number or allowed

    if args.status:
        payload = _build_status_payload(from_number)
    elif args.audio_id:
        payload = _build_audio_payload(args.audio_id, args.wamid, from_number)
    elif args.text:
        payload = _build_text_payload(args.text, args.wamid, from_number)
    else:
        parser.print_help()
        sys.exit(1)

    body = json.dumps(payload).encode()
    signature = _sign(secret, body)

    if args.tamper:
        body = body[:-1] + b"!"  # corrupt last byte
        print("Tampered body (expect 401)...")

    print(f"Sending to {args.url}")
    print(f"wamid={args.wamid} from={from_number} type={'text' if args.text else 'audio' if args.audio_id else 'status'}")

    resp = httpx.post(
        args.url,
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Hub-Signature-256": signature,
        },
        timeout=30,
    )
    print(f"Response: {resp.status_code} {resp.text[:200]}")


if __name__ == "__main__":
    main()
