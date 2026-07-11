from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.hermes import breaker


@pytest.fixture(autouse=True)
def clean_state():
    breaker._state.clear()
    breaker._set_now(lambda: datetime.now(timezone.utc))
    yield
    breaker._state.clear()
    breaker._set_now(lambda: datetime.now(timezone.utc))


def test_three_failures_open_circuit():
    breaker.record_failure("test_provider")
    breaker.record_failure("test_provider")
    assert breaker.is_available("test_provider")  # not yet open after 2
    breaker.record_failure("test_provider")
    assert not breaker.is_available("test_provider")  # open after 3


def test_skip_while_circuit_open():
    for _ in range(3):
        breaker.record_failure("test_provider")
    assert not breaker.is_available("test_provider")
    assert not breaker.is_available("test_provider")  # still blocked


def test_half_open_after_60_seconds():
    for _ in range(3):
        breaker.record_failure("test_provider")
    assert not breaker.is_available("test_provider")

    # Fast-forward 61 seconds
    opened_at = breaker._get("test_provider").circuit_opened_at
    future_time = opened_at + timedelta(seconds=61)
    breaker._set_now(lambda: future_time)

    assert breaker.is_available("test_provider")  # half-open trial allowed
    assert not breaker.is_available("test_provider")  # second caller blocked while trial in flight


def test_success_closes_circuit():
    for _ in range(3):
        breaker.record_failure("test_provider")
    assert not breaker.is_available("test_provider")

    opened_at = breaker._get("test_provider").circuit_opened_at
    breaker._set_now(lambda: opened_at + timedelta(seconds=61))
    assert breaker.is_available("test_provider")  # half-open

    breaker.record_success("test_provider")
    assert breaker.is_available("test_provider")  # closed again
    assert breaker._get("test_provider").consecutive_failures == 0


def test_failure_during_half_open_reopens():
    for _ in range(3):
        breaker.record_failure("test_provider")

    opened_at = breaker._get("test_provider").circuit_opened_at
    breaker._set_now(lambda: opened_at + timedelta(seconds=61))
    assert breaker.is_available("test_provider")  # claim half-open trial

    breaker.record_failure("test_provider")  # probe failed
    assert not breaker.is_available("test_provider")  # re-opened, 60s timer reset

    # New opened_at should be the current mocked time
    new_opened = breaker._get("test_provider").circuit_opened_at
    assert new_opened > opened_at
