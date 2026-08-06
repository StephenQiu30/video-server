from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from app.core.session import SessionError, SessionManager

NOW = datetime(2026, 8, 6, tzinfo=UTC)


def test_session_round_trip_and_owner_hash() -> None:
    manager = SessionManager(b"s" * 48, ttl_seconds=3600)

    issued = manager.issue(now=NOW)
    verified = manager.verify(issued.token, now=NOW + timedelta(minutes=5))

    assert verified.session_id == issued.session_id
    assert verified.owner_hash == issued.owner_hash
    assert len(verified.owner_hash) == 64


def test_session_rejects_tampering() -> None:
    manager = SessionManager(b"s" * 48, ttl_seconds=3600)
    issued = manager.issue(now=NOW)

    with pytest.raises(SessionError, match="invalid_session"):
        manager.verify(f"{issued.token}x", now=NOW)


def test_session_rejects_expiry() -> None:
    manager = SessionManager(b"s" * 48, ttl_seconds=60)
    issued = manager.issue(now=NOW)

    with pytest.raises(SessionError, match="expired_session"):
        manager.verify(issued.token, now=NOW + timedelta(seconds=61))
