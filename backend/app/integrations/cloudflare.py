from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import httpx

logger = logging.getLogger(__name__)

_BASE = "https://api.cloudflare.com/client/v4"
_TIMEOUT = 15.0


class CloudflareError(Exception):
    pass


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


@dataclass
class EdgeCert:
    zone_id: str
    expires_on: datetime | None
    status: str
    days_remaining: int | None


@dataclass
class FirewallSummary:
    zone_id: str
    event_count: int
    top_countries: list[str]


async def _get(client: httpx.AsyncClient, url: str, token: str) -> dict:
    for attempt in range(2):
        try:
            resp = await client.get(url, headers=_headers(token))
            if resp.status_code >= 500 and attempt == 0:
                continue
            resp.raise_for_status()
            data = resp.json()
            if not data.get("success"):
                errors = data.get("errors", [])
                raise CloudflareError(f"Cloudflare API error: {errors}")
            return data
        except httpx.TimeoutException:
            if attempt == 0:
                continue
            raise CloudflareError("Cloudflare request timed out")
    raise CloudflareError("Cloudflare request failed after retry")


async def get_zone_ssl(zone_id: str, token: str) -> EdgeCert:
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        data = await _get(client, f"{_BASE}/zones/{zone_id}/ssl/certificate_packs", token)
    packs = data.get("result", [])
    active = next(
        (p for p in packs if p.get("type") == "universal" and p.get("status") == "active"),
        packs[0] if packs else None,
    )
    if not active:
        return EdgeCert(zone_id=zone_id, expires_on=None, status="unknown", days_remaining=None)

    expires_str = active.get("certificates", [{}])[0].get("expires_on")
    expires_on: datetime | None = None
    days: int | None = None
    if expires_str:
        try:
            expires_on = datetime.fromisoformat(expires_str.replace("Z", "+00:00"))
            days = (expires_on - datetime.now(timezone.utc)).days
        except ValueError:
            pass

    return EdgeCert(
        zone_id=zone_id,
        expires_on=expires_on,
        status=active.get("status", "unknown"),
        days_remaining=days,
    )


async def recent_firewall_events(zone_id: str, token: str, hours: int = 24) -> FirewallSummary:
    since = (datetime.now(timezone.utc) - timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ")
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        try:
            data = await _get(
                client,
                f"{_BASE}/zones/{zone_id}/firewall/events?since={since}&per_page=100",
                token,
            )
        except CloudflareError:
            return FirewallSummary(zone_id=zone_id, event_count=0, top_countries=[])

    events = data.get("result", [])
    country_counts: dict[str, int] = {}
    for ev in events:
        c = ev.get("clientCountryName", "Unknown")
        country_counts[c] = country_counts.get(c, 0) + 1

    top = sorted(country_counts, key=lambda x: country_counts[x], reverse=True)[:3]
    return FirewallSummary(zone_id=zone_id, event_count=len(events), top_countries=top)
