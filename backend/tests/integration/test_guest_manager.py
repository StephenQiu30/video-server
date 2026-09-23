import asyncio
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from app.core.security.provider_session_cipher import ProviderSessionCipher
from app.integrations.provider_guest_bootstrap import PublicGuestBootstrap
from app.repositories.providers.guest_contexts import GuestContexts
from app.services.provider_guest import GuestScope
from app.services.provider_types import ProviderKey
from app.workers.runner.guest_material import publish_guest_lease, read_guest_lease
from app.workers.runner.provider_guest_manager import (
    GuestManager,
    guest_status_document,
)
from cryptography.fernet import Fernet
from sqlalchemy.ext.asyncio import async_sessionmaker

NOW = datetime(2026, 9, 22, tzinfo=UTC)
SCOPE = GuestScope(ProviderKey.DOUYIN, "douyin-public", "mobile", "egress")


async def test_cold_prepare_encrypted_persistence_restart_and_revocation(
    postgres_engine, tmp_path
):
    calls = []

    def respond(request):
        calls.append(request)
        assert "cookie" not in request.headers
        assert str(request.url) == "https://www.iesdouyin.com/"
        return httpx.Response(
            301,
            headers={
                "set-cookie": (
                    "ttwid=fixture-guest; Domain=.iesdouyin.com; Path=/; Secure"
                ),
                "location": "http://127.0.0.1/never-follow",
            },
        )

    repo = GuestContexts(async_sessionmaker(postgres_engine, expire_on_commit=False))
    cipher = ProviderSessionCipher(Fernet.generate_key().decode())
    bootstrap = PublicGuestBootstrap(
        "http://proxy:3128", transport=httpx.MockTransport(respond)
    )
    clock = [NOW]

    def manager(root):
        return GuestManager(
            repo,
            cipher,
            bootstrap,
            SCOPE,
            root,
            owner="fixture",
            clock=lambda: clock[0],
        )

    first = manager(tmp_path / "first")
    assert await first.tick() == "ready"
    state = await repo.read(SCOPE)
    assert guest_status_document(
        state, SCOPE, tmp_path / "first/cookies.txt", now=NOW
    ) == {
        "provider_key": "douyin",
        "state": "ready",
        "stored_usable": True,
        "published_lease_usable": True,
        "reason_code": None,
        "retry_at": None,
        "valid_until": state.valid_until.isoformat(),
    }
    assert (
        b"fixture-guest" not in state.ciphertext
        and b"fixture-guest" not in repr(state).encode()
    )
    lease = read_guest_lease(tmp_path / "first/cookies.txt", SCOPE, now=NOW)
    assert b"fixture-guest" in lease.payload and "fixture-guest" not in repr(lease)
    # Database material alone is insufficient for the Runner to execute.
    assert not guest_status_document(
        state, SCOPE, tmp_path / "missing/cookies.txt", now=NOW
    )["published_lease_usable"]
    (tmp_path / "first/cookies.txt").write_bytes(b"corrupt")
    unavailable = guest_status_document(
        state, SCOPE, tmp_path / "first/cookies.txt", now=NOW
    )
    assert unavailable["stored_usable"] is True
    assert unavailable["published_lease_usable"] is False
    assert "fixture-guest" not in str(unavailable)
    publish_guest_lease(
        tmp_path / "first/cookies.txt",
        SCOPE,
        state.revision + 1,
        lease.payload,
        now=NOW,
        deadline=NOW + timedelta(seconds=90),
    )
    assert not guest_status_document(
        state, SCOPE, tmp_path / "first/cookies.txt", now=NOW
    )["published_lease_usable"]
    # A new host directory recovers the existing encrypted guest revision.
    clock[0] += timedelta(seconds=10)
    second = manager(tmp_path / "second")
    assert await second.tick() == "ready"
    assert len(calls) == 1
    assert (
        read_guest_lease(tmp_path / "second/cookies.txt", SCOPE, now=clock[0]).version
        == lease.version
    )
    await repo.revoke(SCOPE, now=clock[0])
    assert await second.tick() == "revoked"
    assert not (tmp_path / "second/cookies.txt").exists()
    assert await first.tick() == "revoked"
    assert len(calls) == 1


async def test_challenge_enters_cooldown_without_guest_file(postgres_engine, tmp_path):
    calls = []

    def respond(request):
        calls.append(request)
        return httpx.Response(403, headers={"set-cookie": "ttwid=unverified; Path=/"})

    repo = GuestContexts(async_sessionmaker(postgres_engine, expire_on_commit=False))
    manager = GuestManager(
        repo,
        ProviderSessionCipher(Fernet.generate_key().decode()),
        PublicGuestBootstrap(
            "http://proxy:3128", transport=httpx.MockTransport(respond)
        ),
        SCOPE,
        tmp_path,
        owner="fixture",
        clock=lambda: NOW,
    )
    for _ in range(5):
        assert await manager.tick() == "cooling"
    assert len(calls) == 1
    assert not (tmp_path / "cookies.txt").exists()
    state = await repo.read(SCOPE)
    document = guest_status_document(state, SCOPE, tmp_path / "cookies.txt", now=NOW)
    assert document["state"] == "cooling"
    assert document["reason_code"] == "provider_verification_required"
    assert document["stored_usable"] is False
    assert document["published_lease_usable"] is False
    assert document["retry_at"] == (NOW + timedelta(seconds=30)).isoformat()
    assert "ciphertext" not in document and "unverified" not in str(document)


async def test_corrupt_material_is_cooled_and_automatically_rebuilt(
    postgres_engine, tmp_path
):
    repo = GuestContexts(async_sessionmaker(postgres_engine, expire_on_commit=False))
    lease = await repo.claim(SCOPE, "old", now=NOW)
    await repo.publish(
        lease, b"corrupt", now=NOW, valid_until=NOW + timedelta(minutes=10)
    )
    clock = [NOW]
    calls = []

    def respond(request):
        calls.append(request)
        return httpx.Response(200, headers={"set-cookie": "ttwid=guest; Path=/"})

    manager = GuestManager(
        repo,
        ProviderSessionCipher(Fernet.generate_key().decode()),
        PublicGuestBootstrap(
            "http://proxy:3128", transport=httpx.MockTransport(respond)
        ),
        SCOPE,
        tmp_path,
        owner="new",
        clock=lambda: clock[0],
    )
    assert await manager.tick() == "invalid"
    assert not (tmp_path / "cookies.txt").exists()
    assert await manager.tick() == "cooling"
    assert not calls
    clock[0] += timedelta(seconds=30)
    assert await manager.tick() == "ready"
    assert len(calls) == 1
    assert read_guest_lease(tmp_path / "cookies.txt", SCOPE, now=clock[0]).revision == 2


async def test_database_stall_is_bounded_and_releases_local_lock(tmp_path, monkeypatch):
    cancelled = asyncio.Event()

    class StalledRepository:
        async def recover(self, **kwargs):
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.set()

    timeout = asyncio.timeout

    def short_timeout(delay):
        assert delay == 25
        return timeout(0.01)

    monkeypatch.setattr(asyncio, "timeout", short_timeout)
    manager = GuestManager(
        StalledRepository(),
        None,
        None,
        SCOPE,
        tmp_path,
        owner="fixture",
        clock=lambda: NOW,
    )
    for _ in range(2):
        with pytest.raises(TimeoutError):
            await manager.tick()
    assert cancelled.is_set()
