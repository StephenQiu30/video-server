import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from app.database import create_session_factory
from app.models.email_verification import EmailVerificationRow
from app.repositories.email_verification_repository import SqlAlchemyVerificationStore
from sqlalchemy.ext.asyncio import AsyncEngine
from tests.integration.test_auth_routes import auth_client


@pytest.mark.parametrize("prefix", ["/api/auth", "/api/app/v1/auth"])
async def test_registration_requires_proof_and_consumes_once(
    tmp_path: Path, postgres_engine: AsyncEngine, prefix: str
) -> None:
    credentials = {
        "username": "verified_user",
        "email": "verified@example.com",
        "password": "secure-password",
    }
    async with auth_client(tmp_path, postgres_engine) as client:
        missing = await client.post(prefix + "/register", json=credentials)
        assert missing.status_code == 422
        sent = await client.post(
            prefix + "/registration-code", json={"email": credentials["email"]}
        )
        assert sent.status_code == 200 and sent.json()["email_sent"] is True
        code = client.mailer.codes[credentials["email"]]
        wrong_email = await client.post(
            prefix + "/register",
            json={
                **credentials,
                "email": "other@example.com",
                "verification_code": code,
            },
        )
        assert wrong_email.status_code == 400
        wrong = await client.post(
            prefix + "/register",
            json={
                **credentials,
                "verification_code": "999999" if code != "999999" else "000000",
            },
        )
        assert wrong.status_code == 400
        registered = await client.post(
            prefix + "/register", json={**credentials, "verification_code": code}
        )
        assert registered.status_code == 201
        logged_in = await client.post(
            prefix + "/login", json={k: credentials[k] for k in ("email", "password")}
        )
        assert logged_in.status_code == 200
    sessions = create_session_factory(postgres_engine)
    async with sessions() as session:
        row = await session.get(EmailVerificationRow, credentials["email"])
        assert row is not None and row.consumed and row.code_digest != code


async def test_attempt_expiry_resend_and_atomic_consumption(
    postgres_engine: AsyncEngine,
) -> None:
    sessions = create_session_factory(postgres_engine)
    store = SqlAlchemyVerificationStore(sessions)
    now = datetime.now(UTC)
    email = "atomic@example.com"
    generation = uuid4()
    assert await store.reserve(
        email, generation, "a" * 64, now, now + timedelta(minutes=10)
    )
    assert not await store.consume(email, "a" * 64, now)
    assert await store.mark_sent(email, generation)
    assert not await store.reserve(
        email, uuid4(), "b" * 64, now, now + timedelta(minutes=10)
    )
    for _ in range(5):
        assert not await store.consume(email, "c" * 64, now)
    assert not await store.consume(email, "a" * 64, now)
    later = now + timedelta(seconds=61)
    newer = uuid4()
    assert await store.reserve(
        email, newer, "b" * 64, later, later + timedelta(minutes=10)
    )
    assert not await store.mark_sent(email, generation)
    await store.invalidate(email, generation)
    assert await store.mark_sent(email, newer)
    assert not await store.consume(email, "a" * 64, later)
    outcomes = await asyncio.gather(
        *(store.consume(email, "b" * 64, later) for _ in range(3))
    )
    assert outcomes.count(True) == 1
    latest = later + timedelta(seconds=61)
    last_id = uuid4()
    assert await store.reserve(
        email, last_id, "d" * 64, latest, latest + timedelta(minutes=10)
    )
    assert await store.mark_sent(email, last_id)
    assert not await store.consume(email, "d" * 64, latest + timedelta(minutes=10))
