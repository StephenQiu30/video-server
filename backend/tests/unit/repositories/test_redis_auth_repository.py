from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from app.repositories.redis_auth_repository import RedisAuthSessionStore
from app.services.auth import SessionRotationConflict


async def test_rotated_refresh_tombstone_is_detected() -> None:
    store = RedisAuthSessionStore("redis://127.0.0.1:6379/0")
    store._client.get = AsyncMock(return_value=f"rotated:{uuid4()}")

    assert await store.user_id_for_session("old-token-hash") is None
    assert await store.is_rotated("old-token-hash")


async def test_atomic_rotation_reports_an_existing_tombstone() -> None:
    store = RedisAuthSessionStore("redis://127.0.0.1:6379/0")
    store._client.eval = AsyncMock(return_value=2)
    now = datetime.now(UTC)

    with pytest.raises(SessionRotationConflict):
        await store.replace_session(
            previous_token_hash="a" * 64,
            session_id=uuid4(),
            user_id=uuid4(),
            token_hash="b" * 64,
            expires_at=now + timedelta(minutes=5),
            now=now,
        )
