from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from app.core.db import create_session_factory
from app.integrations.passwords import Argon2PasswordHasher
from app.models.auth import UserRow
from app.workers.bootstrap_admin import create_first_admin, load_database_url
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine


def test_bootstrap_uses_selected_env_file_not_process_database(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    selected = tmp_path / "selected.env"
    selected.write_text("DATABASE_URL=postgresql+asyncpg://chosen/example\n")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://wrong/example")
    assert load_database_url(selected) == "postgresql+asyncpg://chosen/example"
    with pytest.raises(ValueError, match="environment file does not exist"):
        load_database_url(tmp_path / "missing.env")


@pytest.mark.asyncio
async def test_first_admin_is_atomic_and_cannot_run_after_any_user(
    postgres_engine: AsyncEngine,
) -> None:
    sessions = create_session_factory(postgres_engine)
    results = await asyncio.gather(
        create_first_admin(
            sessions,
            username="FirstAdmin",
            email="first@example.com",
            password="strong-first-password",
        ),
        create_first_admin(
            sessions,
            username="SecondAdmin",
            email="second@example.com",
            password="strong-second-password",
        ),
    )
    assert sorted(results) == [False, True]
    async with sessions() as session:
        users = (await session.scalars(select(UserRow))).all()
    assert len(users) == 1
    assert users[0].role == "admin"
    assert (
        await Argon2PasswordHasher().verify(
            "strong-first-password"
            if users[0].email == "first@example.com"
            else "strong-second-password",
            users[0].password_hash,
        )
    ).valid
    assert not await create_first_admin(
        sessions,
        username="LaterAdmin",
        email="later@example.com",
        password="strong-later-password",
    )
