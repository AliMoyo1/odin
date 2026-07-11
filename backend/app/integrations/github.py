from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)

_BASE = "https://api.github.com"
_TIMEOUT = 15.0


class GitHubError(Exception):
    pass


def _headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


@dataclass
class Issue:
    number: int
    title: str
    state: str
    url: str


async def list_open_issues(repo: str, token: str, limit: int = 10) -> list[Issue]:
    """repo format: 'owner/name'"""
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        for attempt in range(2):
            try:
                resp = await client.get(
                    f"{_BASE}/repos/{repo}/issues",
                    headers=_headers(token),
                    params={"state": "open", "per_page": limit},
                )
                if resp.status_code >= 500 and attempt == 0:
                    continue
                resp.raise_for_status()
                break
            except httpx.TimeoutException:
                if attempt == 0:
                    continue
                raise GitHubError("GitHub request timed out")
        else:
            raise GitHubError("GitHub request failed after retry")

    issues = resp.json()
    if not isinstance(issues, list):
        raise GitHubError(f"Unexpected GitHub response: {issues}")

    return [
        Issue(
            number=i["number"],
            title=i["title"],
            state=i["state"],
            url=i["html_url"],
        )
        for i in issues
        if not i.get("pull_request")  # exclude PRs from issues list
    ]
