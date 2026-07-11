from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable

import structlog

from app.metrics import llm_calls_total

logger = structlog.get_logger(service="breaker")

OPEN_THRESHOLD = 3
HALF_OPEN_AFTER = 60.0  # seconds


@dataclass
class ProviderState:
    consecutive_failures: int = 0
    circuit_open: bool = False
    circuit_opened_at: datetime | None = None
    half_open_trial: bool = False  # True while the half-open probe is in flight


_state: dict[str, ProviderState] = {}
_now: Callable[[], datetime] = lambda: datetime.now(timezone.utc)


def _get(provider: str) -> ProviderState:
    if provider not in _state:
        _state[provider] = ProviderState()
    return _state[provider]


def is_available(provider: str) -> bool:
    s = _get(provider)
    if not s.circuit_open:
        return True
    if s.half_open_trial:
        return False  # probe already in flight
    now = _now()
    if s.circuit_opened_at and (now - s.circuit_opened_at).total_seconds() >= HALF_OPEN_AFTER:
        s.half_open_trial = True
        return True
    return False


def _schedule_persist(provider: str, s: ProviderState) -> None:
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_persist(provider, s))
    except RuntimeError:
        pass  # no running loop in sync contexts; persistence is observability only


def record_success(provider: str) -> None:
    s = _get(provider)
    s.consecutive_failures = 0
    s.circuit_open = False
    s.circuit_opened_at = None
    s.half_open_trial = False
    llm_calls_total.labels(provider=provider, outcome="success").inc()
    logger.info("provider_success", provider=provider)
    _schedule_persist(provider, s)


def record_failure(provider: str) -> None:
    s = _get(provider)
    was_half_open = s.half_open_trial
    s.consecutive_failures += 1
    s.half_open_trial = False
    if s.consecutive_failures >= OPEN_THRESHOLD or was_half_open:
        if not s.circuit_open or was_half_open:
            s.circuit_open = True
            s.circuit_opened_at = _now()
            logger.warning("circuit_opened", provider=provider)
    llm_calls_total.labels(provider=provider, outcome="failure").inc()
    _schedule_persist(provider, s)


def reset(provider: str) -> None:
    """Reset state entirely. Used in tests and smoke."""
    _state.pop(provider, None)


def get_state_snapshot(provider: str) -> dict:
    s = _get(provider)
    return {
        "provider": provider,
        "circuit_open": s.circuit_open,
        "consecutive_failures": s.consecutive_failures,
        "circuit_opened_at": s.circuit_opened_at.isoformat() if s.circuit_opened_at else None,
    }


async def _persist(provider: str, s: ProviderState) -> None:
    try:
        from app.db import async_session
        from sqlalchemy import text
        state_str = "open" if s.circuit_open else ("half_open" if s.half_open_trial else "closed")
        async with async_session() as session:
            await session.execute(
                text("""
                    INSERT INTO llm_provider_health (provider, circuit_state, consecutive_failures, circuit_opened_at, updated_at)
                    VALUES (:p, :cs, :cf, :co, now())
                    ON CONFLICT (provider) DO UPDATE
                    SET circuit_state = EXCLUDED.circuit_state,
                        consecutive_failures = EXCLUDED.consecutive_failures,
                        circuit_opened_at = EXCLUDED.circuit_opened_at,
                        updated_at = now()
                """),
                {"p": provider, "cs": state_str, "cf": s.consecutive_failures, "co": s.circuit_opened_at},
            )
            await session.commit()
    except Exception:
        pass  # observability write; never crash the hot path


def _set_now(fn: Callable[[], datetime]) -> None:
    """Inject a clock function. Used in tests to fast-forward time."""
    global _now
    _now = fn
