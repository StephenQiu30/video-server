from __future__ import annotations

import asyncio
import hashlib
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest
from app.core.db import create_session_factory
from app.core.errors import AppError
from app.models.auth import AuthSessionRow, UserRow
from app.models.web_session import WebSessionRow
from app.repositories.auth.user_repository import SqlAlchemyUserRepository
from app.repositories.auth.web_sessions import WebSessionRepository
from app.services.auth.errors import AuthError, SessionStoreUnavailable
from app.services.auth.web_sessions import WebSessionService
from sqlalchemy import select


async def test_opaque_session_concurrency_expiry_revocation_and_recreation(
    postgres_engine,
):
    sessions = create_session_factory(postgres_engine)
    now = datetime(2026, 9, 22, tzinfo=UTC)
    clock = [now]
    async with sessions.begin() as db:
        user = UserRow(
            username="session_user",
            normalized_username="session_user",
            email="session@example.com",
            password_hash="not-used",
        )
        db.add(user)
        await db.flush()
        user_id = user.id

    def service():
        return WebSessionService(
            WebSessionRepository(sessions),
            now=lambda: clock[0],
            idle_ttl=timedelta(minutes=5),
            absolute_ttl=timedelta(minutes=10),
        )

    web = service()
    grant = await web.issue(user_id)
    assert len(grant.token) == 43
    assert grant.token not in repr(grant)
    async with sessions() as db:
        row = await db.scalar(select(WebSessionRow))
        assert row.token_hash == hashlib.sha256(grant.token.encode()).hexdigest()
        assert (await db.scalar(select(AuthSessionRow))) is None
    clock[0] += timedelta(minutes=2)
    users = await asyncio.gather(
        *(service().current_user(grant.token) for _ in range(50))
    )
    assert {u.id for u in users} == {user_id}
    async with sessions() as db:
        row = await db.scalar(select(WebSessionRow))
        assert row.last_seen_at == clock[0]
        assert row.idle_expires_at == clock[0] + timedelta(minutes=5)
    # Socket heartbeat/read-only probes do not extend inactivity.
    clock[0] += timedelta(minutes=4)
    await web.current_user(grant.token, touch=False)
    clock[0] += timedelta(minutes=1)
    with pytest.raises(AuthError):
        await web.current_user(grant.token)
    replacement = await web.issue(user_id, previous_token=grant.token)
    for _ in range(3):
        clock[0] += timedelta(minutes=3)
        await web.current_user(replacement.token)
    clock[0] += timedelta(minutes=1)
    with pytest.raises(AuthError):
        await web.current_user(replacement.token)
    live = await web.issue(user_id)
    assert await service().revoke(live.token) == user_id
    assert await service().revoke(live.token) is None
    with pytest.raises(AuthError):
        await service().current_user(live.token)


async def test_disabled_account_cannot_revive_old_sessions_on_reactivation(
    postgres_engine,
):
    sessions = create_session_factory(postgres_engine)
    now = datetime.now(UTC)
    async with sessions.begin() as db:
        user = UserRow(
            username="inactive_user",
            normalized_username="inactive_user",
            email="inactive@example.com",
            password_hash="not-used",
        )
        db.add(user)
        await db.flush()
        user_id = user.id
    web = WebSessionService(
        WebSessionRepository(sessions),
        now=lambda: now,
        idle_ttl=timedelta(days=7),
        absolute_ttl=timedelta(days=30),
    )
    grant = await web.issue(user_id)
    users = SqlAlchemyUserRepository(sessions)
    await users.update_account_access(
        account_id=user_id, role=None, is_active=False, quota=None, now=now
    )
    with pytest.raises(AuthError):
        await web.issue(user_id)
    await users.update_account_access(
        account_id=user_id, role=None, is_active=True, quota=None, now=now
    )
    with pytest.raises(AuthError):
        await web.current_user(grant.token)
    await web.issue(user_id)


@pytest.mark.parametrize("operation", ["read", "issue", "revoke"])
async def test_dependency_failure_is_recoverable_not_unauthenticated(operation):
    repository = AsyncMock()
    repository.current_user.side_effect = SessionStoreUnavailable
    repository.create.side_effect = SessionStoreUnavailable
    repository.revoke.side_effect = SessionStoreUnavailable
    web = WebSessionService(
        repository,
        now=lambda: datetime.now(UTC),
        idle_ttl=timedelta(days=7),
        absolute_ttl=timedelta(days=30),
    )
    from uuid import uuid4

    action = {
        "read": lambda: web.current_user("a" * 43),
        "issue": lambda: web.issue(uuid4()),
        "revoke": lambda: web.revoke("a" * 43),
    }[operation]
    with pytest.raises(AppError) as caught:
        await action()
    assert caught.value.status == 503
    assert caught.value.code == "service_unavailable"


async def test_web_session_schema_can_bootstrap_and_repeat_without_reviving():
    from pathlib import Path
    from uuid import uuid4

    from sqlalchemy import text
    from tests.postgres import isolated_postgres_engine

    sql = (Path(__file__).resolve().parents[2] / "sql/schema.sql").read_text()
    async with isolated_postgres_engine() as engine:
        async with engine.connect() as db:
            schema = await db.scalar(text("SELECT current_schema()"))
            assert schema.startswith("test_") and schema.replace("_", "").isalnum()
            await db.execute(text(f'SET search_path TO "{schema}", public'))
            await db.commit()
            raw = await db.get_raw_connection()
            driver = raw.driver_connection
            await driver.execute(sql)
            user_id = await driver.fetchval(
                "INSERT INTO users(id, username, normalized_username, email, "
                "password_hash) VALUES ($1, 'schema_user', 'schema_user', "
                "'schema@example.com', 'unused') RETURNING id",
                uuid4(),
            )
            await driver.execute(
                "INSERT INTO web_sessions(id, user_id, token_hash, created_at, "
                "last_seen_at, idle_expires_at, absolute_expires_at, revoked_at) "
                "VALUES ($3, $1, $2, now(), now(), now() + interval '1 day', "
                "now() + interval '7 days', now())",
                user_id,
                "a" * 64,
                uuid4(),
            )
            await driver.execute(sql)
            row = await driver.fetchrow("SELECT * FROM web_sessions")
            assert row["revoked_at"] is not None
