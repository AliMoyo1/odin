from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)

_BASE = "https://api.hetzner.cloud/v1"
_TIMEOUT = 15.0


class HetznerError(Exception):
    pass


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@dataclass
class ServerInfo:
    id: int
    name: str
    status: str
    datacenter: str
    server_type: str


async def list_servers(token: str) -> list[ServerInfo]:
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        for attempt in range(2):
            try:
                resp = await client.get(f"{_BASE}/servers", headers=_headers(token))
                if resp.status_code >= 500 and attempt == 0:
                    continue
                resp.raise_for_status()
                break
            except httpx.TimeoutException:
                if attempt == 0:
                    continue
                raise HetznerError("Hetzner request timed out")
        else:
            raise HetznerError("Hetzner request failed after retry")

    servers = resp.json().get("servers", [])
    result = []
    for s in servers:
        result.append(ServerInfo(
            id=s["id"],
            name=s["name"],
            status=s.get("status", "unknown"),
            datacenter=s.get("datacenter", {}).get("name", "unknown"),
            server_type=s.get("server_type", {}).get("name", "unknown"),
        ))
    return result
