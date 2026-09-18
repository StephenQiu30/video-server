import asyncio
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from time import perf_counter
from uuid import uuid4

import pytest
from app.database import create_session_factory
from app.domain.provider_access import ProviderAccessPolicy
from app.domain.providers import ProviderAccessMode
from app.models import DownloadJobRow
from app.models.provider_route_cooldown import ProviderRouteCooldownRow
from app.repositories.download_repository import SqlAlchemyDownloadRepository
from app.repositories.provider_route_cooldowns import SqlAlchemyProviderRouteCooldowns
from app.services.downloads import DownloadCreate, FormatCreate, InspectionCreate
from app.services.provider_route_admission import (
    ProviderRouteKey,
    RouteAdmissionUnavailable,
    RouteCoolingDown,
)
from sqlalchemy import delete, select, update
from tests.unit.integrations.test_media_runner_router import context

KEY = ProviderRouteKey("youtube", ProviderAccessPolicy.PUBLIC, "controlled-egress")


async def test_bounded_twenty_concurrent_two_hundred_admissions(postgres_engine):
    repo = SqlAlchemyProviderRouteCooldowns(create_session_factory(postgres_engine))
    await repo.block(KEY, until=datetime.now(UTC) + timedelta(minutes=5))
    semaphore = asyncio.Semaphore(20)
    latencies = []

    async def read(index):
        async with semaphore:
            started = perf_counter()
            with pytest.raises(RouteCoolingDown):
                await repo.acquire(KEY, f"bounded-{index}")
            latencies.append((perf_counter() - started) * 1000)

    async with asyncio.timeout(10):
        await asyncio.gather(*(read(index) for index in range(200)))
    ordered = sorted(latencies)
    print(
        {
            "scope": "isolated-postgres-admission",
            "concurrency": 20,
            "requests": 200,
            "expected_denials": len(ordered),
            "p50_ms": round(ordered[99], 2),
            "p95_ms": round(ordered[189], 2),
            "max_ms": round(ordered[-1], 2),
        }
    )


async def test_held_database_lock_is_bounded_and_does_not_open_route(postgres_engine):
    sessions = create_session_factory(postgres_engine)
    repo = SqlAlchemyProviderRouteCooldowns(sessions)
    await repo.block(KEY, until=datetime.now(UTC) + timedelta(minutes=5))
    async with sessions() as holder, holder.begin():
        await holder.execute(select(ProviderRouteCooldownRow).with_for_update())
        started = perf_counter()
        with pytest.raises(RouteAdmissionUnavailable):
            await repo.acquire(KEY, "blocked-waiter")
        assert perf_counter() - started < 3
    with pytest.raises(RouteCoolingDown):
        await repo.acquire(KEY, "after-lock-release")


async def test_limits_survive_repository_restart_and_merge_concurrent_deadlines(
    postgres_engine,
):
    sessions = create_session_factory(postgres_engine)
    repo = SqlAlchemyProviderRouteCooldowns(sessions)
    until = datetime.now(UTC) + timedelta(minutes=10)
    await asyncio.gather(
        *(repo.block(KEY, until=until - timedelta(seconds=i)) for i in range(20))
    )
    restarted = SqlAlchemyProviderRouteCooldowns(sessions)
    with pytest.raises(RouteCoolingDown) as rejected:
        await restarted.acquire(KEY, "new-process")
    assert rejected.value.retry_at >= until


async def test_only_one_half_open_probe_and_old_success_cannot_clear_new_limit(
    postgres_engine,
):
    sessions = create_session_factory(postgres_engine)
    repo = SqlAlchemyProviderRouteCooldowns(sessions)
    await repo.block(KEY, until=datetime.now(UTC) - timedelta(seconds=1))
    results = await asyncio.gather(
        *(repo.acquire(KEY, f"probe-{i}") for i in range(20)), return_exceptions=True
    )
    leases = [result for result in results if not isinstance(result, BaseException)]
    assert len(leases) == 1
    assert sum(isinstance(result, RouteCoolingDown) for result in results) == 19
    await repo.block(KEY, until=datetime.now(UTC) + timedelta(minutes=5))
    with pytest.raises(RouteCoolingDown):
        await repo.finish(leases[0], success=True)
    with pytest.raises(RouteCoolingDown):
        await repo.acquire(KEY, "after-stale-success")


async def test_success_closes_without_deleting_fencing_generation(postgres_engine):
    repo = SqlAlchemyProviderRouteCooldowns(create_session_factory(postgres_engine))
    await repo.block(KEY, until=datetime.now(UTC) - timedelta(seconds=1))
    lease = await repo.acquire(KEY, "probe")
    assert lease.version is not None
    await repo.finish(lease, success=True)
    assert (await repo.acquire(KEY, "normal")).version is None
    await repo.block(KEY, until=datetime.now(UTC) - timedelta(seconds=1))
    newer = await repo.acquire(KEY, "new-probe")
    assert newer.version > lease.version


async def test_crashed_probe_expires_and_cannot_publish_after_reacquisition(
    postgres_engine,
):
    sessions = create_session_factory(postgres_engine)
    repo = SqlAlchemyProviderRouteCooldowns(sessions)
    past = datetime.now(UTC) - timedelta(seconds=1)
    await repo.block(KEY, until=past)
    old = await repo.acquire(KEY, "crashed")
    async with sessions() as session, session.begin():
        await session.execute(
            update(ProviderRouteCooldownRow).values(probe_lease_until=past)
        )
    current = await SqlAlchemyProviderRouteCooldowns(sessions).acquire(KEY, "restarted")
    with pytest.raises(RouteCoolingDown):
        await repo.finish(old, success=True)
    await repo.finish(current, success=True)


async def test_worker_defers_without_spending_attempt_and_delete_cannot_reset(
    postgres_engine,
):
    sessions = create_session_factory(postgres_engine)
    cooldowns, jobs = (
        SqlAlchemyProviderRouteCooldowns(sessions),
        SqlAlchemyDownloadRepository(sessions),
    )
    now = datetime.now(UTC)
    inspection_id, format_id, job_id = uuid4(), uuid4(), uuid4()
    access = replace(
        context(ProviderAccessMode.ANONYMOUS),
        provider_key=KEY.provider_key,
        egress_affinity_id=KEY.egress_binding_id,
    )
    await jobs.save_inspection(
        InspectionCreate(
            id=inspection_id,
            owner_hash="a" * 64,
            idempotency_key="inspection",
            request_fingerprint="i" * 64,
            url_ciphertext=b"controlled",
            url_nonce=b"nonce",
            url_key_id="fernet",
            extractor_key="Youtube",
            provider_media_id="owned",
            title="Owned fixture",
            duration_seconds=10,
            metadata={"provider_access_context": access.to_document()},
            expires_at=now + timedelta(hours=1),
            formats=(
                FormatCreate(
                    id=format_id,
                    display_name="test",
                    plan_fingerprint="p" * 64,
                    semantic_plan={},
                    provider_hints={},
                    expires_at=now + timedelta(hours=1),
                ),
            ),
        )
    )

    async def new_job(identifier):
        await jobs.create_job(
            DownloadCreate(
                id=identifier,
                inspection_id=inspection_id,
                format_id=format_id,
                owner_hash="a" * 64,
                idempotency_key=identifier.hex,
                request_fingerprint=identifier.hex * 2,
                semantic_plan={},
            ),
            now=now,
        )

    await new_job(job_id)
    until = now + timedelta(minutes=5)
    await cooldowns.block(KEY, until=until)
    assert await jobs.claim_job(job_id, "worker", now, timedelta(minutes=1)) is None
    snapshot = await jobs.get_job(job_id)
    assert snapshot.status == "retry_wait"
    assert snapshot.attempt == 0
    assert snapshot.retry_at >= until
    # The current deletion path physically removes jobs; there is no cooldown FK.
    async with sessions() as session, session.begin():
        await session.execute(delete(DownloadJobRow).where(DownloadJobRow.id == job_id))
    replacement = uuid4()
    await new_job(replacement)
    assert (
        await jobs.claim_job(replacement, "restarted-worker", now, timedelta(minutes=1))
        is None
    )
    assert (await jobs.get_job(replacement)).attempt == 0
    async with sessions() as session, session.begin():
        await session.execute(
            update(ProviderRouteCooldownRow).values(
                blocked_until=now - timedelta(seconds=1)
            )
        )
        await session.execute(
            update(DownloadJobRow)
            .where(DownloadJobRow.id == replacement)
            .values(status="queued", retry_at=None)
        )
    claimed = await jobs.claim_job(replacement, "worker", now, timedelta(minutes=1))
    assert claimed is not None and claimed.attempt == 1
    lease = await cooldowns.acquire(KEY, f"download_{replacement.hex}_1")
    assert lease.version is not None
    with pytest.raises(RouteCoolingDown):
        await cooldowns.acquire(KEY, "other-worker")
