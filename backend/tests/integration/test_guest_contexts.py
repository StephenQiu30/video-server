import asyncio
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from app.core.security.provider_session_cipher import ProviderSessionCipher
from app.models.provider_guest_context import ProviderGuestContextRow
from app.repositories.errors import LeaseConflict
from app.repositories.providers.guest_contexts import GuestContexts
from app.services.provider_guest import GuestScope
from app.services.provider_types import (
    ProviderAccessContextRef,
    ProviderAccessMode,
    ProviderKey,
)
from cryptography.fernet import Fernet
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import async_sessionmaker
from tests.postgres import isolated_postgres_engine

NOW = datetime(2026, 9, 22, tzinfo=UTC)
SCOPE = GuestScope(ProviderKey.DOUYIN, "douyin-public", "mobile-share", "egress-one")


def repository(engine):
    return GuestContexts(async_sessionmaker(engine, expire_on_commit=False))


async def test_concurrent_guest_preparation_has_one_owner(postgres_engine):
    repo = repository(postgres_engine)
    leases = await asyncio.gather(
        *(repo.claim(SCOPE, f"worker-{i}", now=NOW) for i in range(30))
    )
    assert sum(lease is not None for lease in leases) == 1
    state = await repo.read(SCOPE)
    assert state.state == "preparing" and state.fence == 1
    assert state.ciphertext is None and not state.usable(NOW)


async def test_global_slots_and_single_provider_across_scopes(postgres_engine):
    repo = repository(postgres_engine)
    assert await repo.claim(SCOPE, "worker", now=NOW)
    assert (
        await repo.claim(replace(SCOPE, egress_affinity_id="second"), "worker", now=NOW)
        is None
    )
    assert await repo.claim(
        replace(SCOPE, provider=ProviderKey.WEIBO), "worker", now=NOW
    )
    assert (
        await repo.claim(
            replace(SCOPE, provider=ProviderKey.XIAOHONGSHU), "worker", now=NOW
        )
        is None
    )


async def test_refresh_failure_keeps_old_validity_without_extending_it(postgres_engine):
    repo = repository(postgres_engine)
    lease = await repo.claim(SCOPE, "worker", now=NOW)
    end = NOW + timedelta(seconds=100)
    ready = await repo.publish(
        lease, b"encrypted-version-one", now=NOW, valid_until=end
    )
    assert ready.state == "ready" and ready.revision == 1
    assert await repo.claim(SCOPE, "worker", now=NOW + timedelta(seconds=79)) is None
    refresh = await repo.claim(SCOPE, "worker", now=NOW + timedelta(seconds=80))
    assert (await repo.read(SCOPE)).usable(NOW + timedelta(seconds=80))
    cooling = await repo.fail(
        refresh, "provider_rate_limited", now=NOW + timedelta(seconds=81)
    )
    assert cooling.state == "cooling" and cooling.valid_until == end
    assert cooling.usable(NOW + timedelta(seconds=99))
    assert not cooling.usable(end)
    assert await repo.claim(SCOPE, "other", now=end) is None
    assert await repo.recover(now=end) == 1
    assert (await repo.read(SCOPE)).ciphertext is None
    recovered = await repo.claim(SCOPE, "other", now=cooling.retry_at)
    assert recovered.fence > refresh.fence


async def test_stale_publication_cannot_overwrite_new_owner_or_revocation(
    postgres_engine,
):
    repo = repository(postgres_engine)
    old = await repo.claim(SCOPE, "old", now=NOW)
    current = await repo.claim(SCOPE, "new", now=NOW + timedelta(seconds=61))
    with pytest.raises(LeaseConflict):
        await repo.publish(
            old,
            b"old",
            now=NOW + timedelta(seconds=62),
            valid_until=NOW + timedelta(minutes=5),
        )
    await repo.revoke(SCOPE, now=NOW + timedelta(seconds=63))
    with pytest.raises(LeaseConflict):
        await repo.publish(
            current,
            b"new",
            now=NOW + timedelta(seconds=64),
            valid_until=NOW + timedelta(minutes=5),
        )
    assert await repo.claim(SCOPE, "later", now=NOW + timedelta(hours=2)) is None
    assert (await repo.read(SCOPE)).state == "revoked"


async def test_revoke_absent_scope_and_expired_maintenance_cooldown(postgres_engine):
    repo = repository(postgres_engine)
    await repo.revoke(SCOPE, now=NOW)
    assert await repo.claim(SCOPE, "worker", now=NOW) is None
    other = replace(SCOPE, provider=ProviderKey.WEIBO)
    await repo.claim(other, "worker", now=NOW)
    assert await repo.recover(now=NOW + timedelta(seconds=61)) == 1
    observed = await repo.read(other)
    assert observed.state == "cooling" and observed.reason_code == "inspection_timeout"
    assert await repo.claim(other, "new", now=NOW + timedelta(seconds=62)) is None
    assert await repo.claim(other, "new", now=observed.retry_at)


async def test_repeated_guest_failures_back_off_and_reject_raw_error(postgres_engine):
    repo = repository(postgres_engine)
    now = NOW
    for delay in (30, 60, 120, 240, 300, 300):
        lease = await repo.claim(SCOPE, "worker", now=now)
        with pytest.raises(ValueError, match="stable reason"):
            await repo.fail(lease, "Cookie: sensitive-value", now=now)
        state = await repo.fail(lease, "provider_temporarily_unavailable", now=now)
        assert state.retry_at == now + timedelta(seconds=delay)
        now = state.retry_at


def test_guest_cipher_binds_kind_scope_revision_and_deadline():
    cipher = ProviderSessionCipher(Fernet.generate_key().decode())
    end = NOW + timedelta(minutes=5)
    encrypted = cipher.encrypt_guest(SCOPE, 1, end, b"guest-material")
    assert cipher.decrypt_guest(SCOPE, 1, end, encrypted) == b"guest-material"
    for scope in (
        replace(SCOPE, provider=ProviderKey.WEIBO),
        replace(SCOPE, client_profile_id="other"),
        replace(SCOPE, profile_version="other"),
        replace(SCOPE, egress_affinity_id="other"),
    ):
        with pytest.raises(ValueError, match="binding"):
            cipher.decrypt_guest(scope, 1, end, encrypted)
    with pytest.raises(ValueError, match="binding"):
        cipher.decrypt_guest(SCOPE, 2, end, encrypted)
    with pytest.raises(ValueError, match="binding"):
        cipher.decrypt_guest(SCOPE, 1, end + timedelta(seconds=1), encrypted)
    with pytest.raises(ValueError, match="binding"):
        cipher.decrypt(SCOPE.provider, 1, end, encrypted)
    account = cipher.encrypt(SCOPE.provider, 1, end, b"account-material")
    with pytest.raises(ValueError, match="binding"):
        cipher.decrypt_guest(SCOPE, 1, end, account)


async def test_invalidation_cannot_erase_newer_publication(postgres_engine):
    repo = repository(postgres_engine)
    lease = await repo.claim(SCOPE, "one", now=NOW)
    observed = await repo.publish(
        lease, b"bad", now=NOW, valid_until=NOW + timedelta(seconds=100)
    )
    refresh = await repo.claim(SCOPE, "two", now=NOW + timedelta(seconds=81))
    assert not await repo.invalidate(observed, now=NOW + timedelta(seconds=82))
    current = await repo.publish(
        refresh,
        b"new",
        now=NOW + timedelta(seconds=83),
        valid_until=NOW + timedelta(minutes=5),
    )
    assert not await repo.invalidate(observed, now=NOW + timedelta(seconds=84))
    assert await repo.invalidate(current, now=NOW + timedelta(seconds=85))
    state = await repo.read(SCOPE)
    assert state.state == "cooling" and state.ciphertext is None
    assert await repo.claim(SCOPE, "three", now=NOW + timedelta(seconds=86)) is None
    assert await repo.claim(SCOPE, "three", now=state.retry_at)


async def test_guest_schema_empty_and_repeated_preserves_active_lease():
    sql = (Path(__file__).resolve().parents[2] / "sql/schema.sql").read_text()
    async with isolated_postgres_engine() as engine:

        async def apply_schema():
            async with engine.connect() as connection:
                schema = await connection.scalar(text("SELECT current_schema()"))
                assert schema.startswith("test_") and schema.replace("_", "").isalnum()
                await connection.execute(text(f'SET search_path TO "{schema}", public'))
                await connection.commit()
                raw = await connection.get_raw_connection()
                await raw.driver_connection.execute(sql)

        await apply_schema()
        repo = repository(engine)
        lease = await repo.claim(SCOPE, "worker", now=NOW)
        await apply_schema()
        async with engine.connect() as connection:
            columns = await connection.run_sync(
                lambda conn: inspect(conn).get_columns("provider_guest_contexts")
            )
            assert {column["name"] for column in columns} == set(
                ProviderGuestContextRow.__table__.columns.keys()
            )
            assert (
                await connection.scalar(
                    text("SELECT count(*) FROM provider_guest_contexts")
                )
                == 1
            )
        assert await repo.claim(SCOPE, "other", now=NOW) is None
        assert (
            await repo.publish(
                lease, b"encrypted", now=NOW, valid_until=NOW + timedelta(minutes=5)
            )
        ).state == "ready"


async def test_upstream_guest_rejection_expires_only_matching_revision(postgres_engine):
    repo = repository(postgres_engine)
    now = datetime.now(UTC)
    lease = await repo.claim(SCOPE, "worker", now=now)
    await repo.publish(
        lease, b"visitor", now=now, valid_until=now + timedelta(minutes=15)
    )
    context = ProviderAccessContextRef(
        provider_key="douyin",
        profile_version=SCOPE.profile_version,
        access_mode=ProviderAccessMode.GUEST,
        credential_version_id="guest-0",
        egress_affinity_id=SCOPE.egress_affinity_id,
        client_profile_id=SCOPE.client_profile_id,
        attestation_provider_version=None,
        engine_commit="test",
    )
    await repo.reject(context)
    assert (await repo.read(SCOPE)).state == "ready"
    await repo.reject(replace(context, credential_version_id="guest-1"))
    current = await repo.read(SCOPE)
    assert current.state == "cooling" and current.ciphertext is None
    assert current.reason_code == "provider_guest_context_required"
    assert await repo.claim(SCOPE, "refresh", now=current.retry_at) is not None
