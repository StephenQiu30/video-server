from __future__ import annotations

import asyncio
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from app.core.db import create_session_factory
from app.core.security.provider_session_cipher import ProviderSessionCipher
from app.repositories.providers.session_sources import (
    ProviderSessionSources,
    SourceRevisionConflict,
)
from app.services.provider_types import ProviderKey, ProviderSessionVersion
from app.workers.runner.errors import RunnerFailure
from app.workers.runner.provider_cookie_file import ProviderCookieFile
from app.workers.runner.provider_source_replica import ProviderSourceReplica
from cryptography.fernet import Fernet
from sqlalchemy.ext.asyncio import AsyncEngine

PAYLOAD = (
    b"# Netscape HTTP Cookie File\n"
    b".youtube.com\tTRUE\t/\tTRUE\t0\tSID\tsynthetic-session\n"
)
PROVIDER = ProviderKey.YOUTUBE


async def seed(
    sources: ProviderSessionSources,
    cipher: ProviderSessionCipher,
    *,
    expected: int = 0,
    expiry: datetime | None = None,
    payload: bytes = PAYLOAD,
) -> int:
    expires = expiry or datetime.now(UTC) + timedelta(hours=1)
    return await sources.publish(
        PROVIDER,
        expected_revision=expected,
        valid_until=expires,
        ciphertext=cipher.encrypt(PROVIDER, expected + 1, expires, payload),
    )


def read(root: Path) -> bytes:
    return ProviderCookieFile(root / "youtube/cookies.txt", require_lease=True).read(
        PROVIDER, ProviderSessionVersion.BROWSER
    )


async def test_empty_new_machine_restores_same_source_and_revocation_survives_restart(
    postgres_engine: AsyncEngine, tmp_path: Path
) -> None:
    sources = ProviderSessionSources(create_session_factory(postgres_engine))
    key = Fernet.generate_key().decode()
    cipher = ProviderSessionCipher(key)
    await seed(sources, cipher)
    first = ProviderSourceReplica(sources, cipher, tmp_path / "host-a")
    second = ProviderSourceReplica(
        sources, ProviderSessionCipher(key), tmp_path / "host-b"
    )
    assert await first.sync(PROVIDER) == "ready"
    assert await second.sync(PROVIDER) == "ready"
    assert read(tmp_path / "host-a") == read(tmp_path / "host-b")
    assert read(tmp_path / "host-a").endswith(PAYLOAD.split(b"\n", 1)[1])
    row = await sources.read(PROVIDER)
    assert row is not None and row.ciphertext is not None
    assert b"synthetic-session" not in row.ciphertext

    await sources.publish(
        PROVIDER, expected_revision=1, ciphertext=None, valid_until=None
    )
    for replica in (first, second):
        assert await replica.sync(PROVIDER) == "unavailable"
    with pytest.raises(SourceRevisionConflict):
        await seed(sources, cipher, expected=1)
    restarted = ProviderSourceReplica(sources, cipher, tmp_path / "host-c")
    assert await restarted.sync(PROVIDER) == "unavailable"
    assert not (tmp_path / "host-c/youtube/cookies.txt").exists()

    # Explicit new authorization is allowed, but cannot revive old contexts.
    await seed(sources, cipher, expected=2)
    assert await restarted.sync(PROVIDER) == "ready"
    assert b"source revision: youtube 3" in read(tmp_path / "host-c")


async def test_concurrent_publication_has_one_winner(
    postgres_engine: AsyncEngine,
) -> None:
    sources = ProviderSessionSources(create_session_factory(postgres_engine))
    cipher = ProviderSessionCipher(Fernet.generate_key().decode())
    results = await asyncio.gather(
        *(seed(sources, cipher) for _ in range(12)), return_exceptions=True
    )
    assert results.count(1) == 1
    assert sum(isinstance(result, SourceRevisionConflict) for result in results) == 11


async def test_renewal_preserves_cookie_identity_and_killed_publisher_lease_expires(
    postgres_engine: AsyncEngine, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sources = ProviderSessionSources(create_session_factory(postgres_engine))
    cipher = ProviderSessionCipher(Fernet.generate_key().decode())
    await seed(sources, cipher)
    replica = ProviderSourceReplica(sources, cipher, tmp_path)
    await replica.sync(PROVIDER)
    original = read(tmp_path)
    await replica.sync(PROVIDER)
    assert read(tmp_path) == original
    monkeypatch.setattr(
        "app.workers.runner.provider_cookie_file.time.time",
        lambda: time.time_ns() / 1e9 + 91,
    )
    with pytest.raises(RunnerFailure, match="provider session unavailable"):
        read(tmp_path)


async def test_wrong_key_or_expired_source_removes_local_replica(
    postgres_engine: AsyncEngine, tmp_path: Path
) -> None:
    sources = ProviderSessionSources(create_session_factory(postgres_engine))
    cipher = ProviderSessionCipher(Fernet.generate_key().decode())
    await seed(sources, cipher)
    replica = ProviderSourceReplica(sources, cipher, tmp_path)
    await replica.sync(PROVIDER)
    invalid = ProviderSourceReplica(
        sources, ProviderSessionCipher(Fernet.generate_key().decode()), tmp_path
    )
    assert await invalid.sync(PROVIDER) == "invalid"
    assert not (tmp_path / "youtube/cookies.txt").exists()
    await seed(
        sources, cipher, expected=1, expiry=datetime.now(UTC) - timedelta(seconds=1)
    )
    assert await replica.sync(PROVIDER) == "unavailable"


def test_cipher_binds_provider_revision_and_expiry() -> None:
    cipher = ProviderSessionCipher(Fernet.generate_key().decode())
    expiry = datetime.now(UTC) + timedelta(hours=1)
    token = cipher.encrypt(PROVIDER, 1, expiry, PAYLOAD)
    for provider, revision, deadline in (
        (ProviderKey.REDDIT, 1, expiry),
        (PROVIDER, 2, expiry),
        (PROVIDER, 1, expiry + timedelta(seconds=1)),
    ):
        with pytest.raises(ValueError, match="binding mismatch"):
            cipher.decrypt(provider, revision, deadline, token)


def test_replica_reader_requires_lease(tmp_path: Path) -> None:
    source = tmp_path / "cookies.txt"
    source.write_bytes(PAYLOAD)
    source.chmod(0o600)
    with pytest.raises(RunnerFailure, match="provider session unavailable"):
        ProviderCookieFile(source, require_lease=True).read(
            PROVIDER, ProviderSessionVersion.BROWSER
        )
