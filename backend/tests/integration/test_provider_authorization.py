from __future__ import annotations

import asyncio
import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import pytest
from app.models.provider_authorization import ProviderAuthorizationRow
from app.repositories.providers.authorizations import ProviderAuthorizationRepository
from app.services.provider_authorization import (
    ProviderAuthorizationError,
    ProviderAuthorizationService,
    ProviderAuthorizationStatus,
)
from app.services.provider_types import ProviderAuthorizationSource, ProviderKey
from app.workers.runner.provider_authorization_queue import (
    AUTHORIZATION_READY_MARKER,
    AUTHORIZATION_READY_PAYLOAD,
    FileProviderAuthorizationQueue,
    authorization_runtime,
    prepare_authorization_runtime,
    read_authorization_response,
)
from app.workers.runner.provider_browser_bridge_store import ProviderBrowserBridgeStore
from app.workers.runner.provider_cookie_agent import drain_requests
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

USER_ID = UUID("11111111-1111-4111-8111-111111111111")
OTHER_USER_ID = UUID("22222222-2222-4222-8222-222222222222")


def _service(
    postgres_engine: AsyncEngine,
    tmp_path: Path,
    now: datetime | Callable[[], datetime],
) -> tuple[ProviderAuthorizationService, ProviderAuthorizationRepository]:
    repository = ProviderAuthorizationRepository(
        async_sessionmaker(postgres_engine, expire_on_commit=False)
    )
    control = authorization_runtime(tmp_path)
    prepare_authorization_runtime(tmp_path)
    (control / AUTHORIZATION_READY_MARKER).write_bytes(AUTHORIZATION_READY_PAYLOAD)
    clock = now if callable(now) else lambda: now
    service = ProviderAuthorizationService(
        FileProviderAuthorizationQueue(tmp_path, probe_timeout_seconds=0),
        repository,
        now=clock,
        can_authorize_provider=lambda provider: (
            provider in {ProviderKey.YOUTUBE.value, ProviderKey.DOUYIN.value}
        ),
        transaction_ttl=timedelta(minutes=5),
    )
    return service, repository


@pytest.mark.asyncio
async def test_begin_and_poll_authorization_without_cookie_material(
    postgres_engine: AsyncEngine,
    tmp_path: Path,
) -> None:
    now = datetime(2026, 9, 20, 12, tzinfo=UTC)
    service, _repository = _service(postgres_engine, tmp_path, now)

    transaction = await service.begin(USER_ID, ProviderKey.YOUTUBE.value)
    assert transaction.provider_key == ProviderKey.YOUTUBE.value
    assert transaction.status == ProviderAuthorizationStatus.PENDING
    assert read_authorization_response(tmp_path, transaction.transaction_id) is None

    response_path = (
        tmp_path / "control" / "responses" / f"{transaction.transaction_id}.response"
    )
    response_path.write_bytes(b"source_available\n")
    available = await service.get(USER_ID, transaction.transaction_id)
    assert available.status == ProviderAuthorizationStatus.SOURCE_AVAILABLE
    assert not response_path.exists()

    await service.close()


@pytest.mark.asyncio
async def test_permission_denial_is_exposed_as_actionable_status(
    postgres_engine: AsyncEngine,
    tmp_path: Path,
) -> None:
    service, _repository = _service(
        postgres_engine,
        tmp_path,
        datetime(2026, 9, 20, 12, tzinfo=UTC),
    )

    transaction = await service.begin(USER_ID, ProviderKey.YOUTUBE.value)
    response_path = (
        tmp_path / "control" / "responses" / f"{transaction.transaction_id}.response"
    )
    response_path.write_bytes(b"provider_session_permission_denied\n")

    denied = await service.get(USER_ID, transaction.transaction_id)

    assert denied.status == ProviderAuthorizationStatus.PERMISSION_REQUIRED
    await service.close()


@pytest.mark.asyncio
async def test_authorization_transactions_are_owner_scoped(
    postgres_engine: AsyncEngine,
    tmp_path: Path,
) -> None:
    service, _repository = _service(
        postgres_engine,
        tmp_path,
        datetime(2026, 9, 20, 12, tzinfo=UTC),
    )
    transaction = await service.begin(USER_ID, ProviderKey.DOUYIN.value)

    with pytest.raises(ProviderAuthorizationError, match="授权事务不存在"):
        await service.get(OTHER_USER_ID, transaction.transaction_id)
    with pytest.raises(ProviderAuthorizationError, match="授权事务不存在"):
        await service.cancel(OTHER_USER_ID, transaction.transaction_id)

    await service.cancel(USER_ID, transaction.transaction_id)
    cancelled = await service.get(USER_ID, transaction.transaction_id)
    assert cancelled.status == ProviderAuthorizationStatus.CANCELLED
    await service.close()


@pytest.mark.asyncio
async def test_cancelled_transaction_rejects_a_late_authorization_result(
    postgres_engine: AsyncEngine,
    tmp_path: Path,
) -> None:
    service, _repository = _service(
        postgres_engine,
        tmp_path,
        datetime(2026, 9, 20, 12, tzinfo=UTC),
    )
    transaction = await service.begin(USER_ID, ProviderKey.YOUTUBE.value)
    await service.cancel(USER_ID, transaction.transaction_id)
    response_path = (
        tmp_path / "control" / "responses" / f"{transaction.transaction_id}.response"
    )
    response_path.write_bytes(b"source_available\n")

    result = await service.get(USER_ID, transaction.transaction_id)

    assert result.status == ProviderAuthorizationStatus.CANCELLED
    assert not response_path.exists()
    await service.close()


@pytest.mark.asyncio
async def test_authorization_response_is_retained_when_status_write_fails(
    monkeypatch: pytest.MonkeyPatch,
    postgres_engine: AsyncEngine,
    tmp_path: Path,
) -> None:
    service, repository = _service(
        postgres_engine,
        tmp_path,
        datetime(2026, 9, 20, 12, tzinfo=UTC),
    )
    transaction = await service.begin(USER_ID, ProviderKey.YOUTUBE.value)
    response_path = (
        tmp_path / "control" / "responses" / f"{transaction.transaction_id}.response"
    )
    response_path.write_bytes(b"source_available\n")

    async def fail_transition(*_args: object, **_kwargs: object) -> int:
        raise ConnectionError("simulated database failure")

    monkeypatch.setattr(repository, "transition", fail_transition)
    with pytest.raises(ConnectionError, match="simulated database failure"):
        await service.get(USER_ID, transaction.transaction_id)

    assert response_path.exists()
    await service.close()


@pytest.mark.asyncio
async def test_deadline_wins_over_a_late_authorization_response(
    postgres_engine: AsyncEngine,
    tmp_path: Path,
) -> None:
    current = [datetime(2026, 9, 20, 12, tzinfo=UTC)]
    service, _repository = _service(postgres_engine, tmp_path, lambda: current[0])
    transaction = await service.begin(USER_ID, ProviderKey.YOUTUBE.value)
    response_path = (
        tmp_path / "control" / "responses" / f"{transaction.transaction_id}.response"
    )
    response_path.write_bytes(b"source_available\n")
    current[0] = transaction.expires_at

    result = await service.get(USER_ID, transaction.transaction_id)

    assert result.status == ProviderAuthorizationStatus.EXPIRED
    assert not response_path.exists()
    await service.close()


@pytest.mark.asyncio
async def test_duplicate_active_authorization_reuses_one_transaction(
    postgres_engine: AsyncEngine,
    tmp_path: Path,
) -> None:
    service, _repository = _service(
        postgres_engine,
        tmp_path,
        datetime(2026, 9, 20, 12, tzinfo=UTC),
    )

    first = await service.begin(USER_ID, ProviderKey.YOUTUBE.value)
    second = await service.begin(USER_ID, ProviderKey.YOUTUBE.value)

    assert second == first
    requests = list((tmp_path / "control" / "requests").glob("*.request"))
    assert len(requests) == 1
    await service.close()


@pytest.mark.asyncio
async def test_concurrent_authorization_claim_is_atomic(
    postgres_engine: AsyncEngine,
    tmp_path: Path,
) -> None:
    service, _repository = _service(
        postgres_engine,
        tmp_path,
        datetime(2026, 9, 20, 12, tzinfo=UTC),
    )

    first, second = await asyncio.gather(
        service.begin(USER_ID, ProviderKey.YOUTUBE.value),
        service.begin(USER_ID, ProviderKey.YOUTUBE.value),
    )

    assert second == first
    requests = list((tmp_path / "control" / "requests").glob("*.request"))
    assert len(requests) == 1
    await service.close()


@pytest.mark.asyncio
async def test_shared_provider_rejects_a_competing_owner_or_source(
    postgres_engine: AsyncEngine,
    tmp_path: Path,
) -> None:
    service, _repository = _service(
        postgres_engine,
        tmp_path,
        datetime(2026, 9, 20, 12, tzinfo=UTC),
    )
    first = await service.begin(USER_ID, ProviderKey.YOUTUBE.value)

    with pytest.raises(ProviderAuthorizationError, match="已有管理员授权事务"):
        await service.begin(OTHER_USER_ID, ProviderKey.YOUTUBE.value)
    with pytest.raises(ProviderAuthorizationError, match="已有管理员授权事务"):
        await service.begin(
            USER_ID,
            ProviderKey.YOUTUBE.value,
            ProviderAuthorizationSource.DEDICATED_CHROME,
        )

    requests = list((tmp_path / "control" / "requests").glob("*.request"))
    assert [item.stem for item in requests] == [first.transaction_id]
    await service.close()


async def test_operation_deadline_and_result_retention_survive_service_restart(
    postgres_engine: AsyncEngine,
    tmp_path: Path,
) -> None:
    now = datetime(2026, 9, 20, 12, tzinfo=UTC)
    service, _ = _service(postgres_engine, tmp_path, now)
    transaction = await service.begin(USER_ID, ProviderKey.YOUTUBE.value)
    await service.close()
    restarted, repository = _service(postgres_engine, tmp_path, now)
    response = (
        tmp_path / "control" / "responses" / f"{transaction.transaction_id}.response"
    )
    response.write_bytes(b"source_available\n")
    assert await restarted.reconcile() == 1
    record = await repository.get(
        UUID(hex=transaction.transaction_id), USER_ID, now=now
    )
    assert record.status == ProviderAuthorizationStatus.SOURCE_AVAILABLE
    assert record.expires_at == transaction.expires_at
    async with async_sessionmaker(postgres_engine)() as session:
        row = await session.get(ProviderAuthorizationRow, record.id)
        assert row.retain_until == transaction.expires_at + timedelta(hours=24)
        assert row.purpose == "maintain_deployment_source"
    assert await repository.expired_results(now=transaction.expires_at) == ()
    cleanup_at = transaction.expires_at + timedelta(hours=24)
    expired = await repository.expired_results(now=cleanup_at)
    assert len(expired) == 1
    await repository.forget(expired[0], now=cleanup_at)
    await restarted.close()


@pytest.mark.asyncio
async def test_postgres_and_agent_complete_the_authorization_control_loop(
    tmp_path: Path,
    postgres_engine: AsyncEngine,
) -> None:
    now = datetime.now(UTC)
    control = authorization_runtime(tmp_path)
    prepare_authorization_runtime(tmp_path)
    (control / AUTHORIZATION_READY_MARKER).write_bytes(AUTHORIZATION_READY_PAYLOAD)
    ProviderBrowserBridgeStore(tmp_path).write(
        ProviderKey.YOUTUBE,
        b"# Netscape HTTP Cookie File\n"
        b".youtube.com\tTRUE\t/\tTRUE\t0\tSID\tcurrent-session\n",
    )
    service = ProviderAuthorizationService(
        FileProviderAuthorizationQueue(tmp_path, probe_timeout_seconds=1),
        ProviderAuthorizationRepository(
            async_sessionmaker(postgres_engine, expire_on_commit=False)
        ),
        now=lambda: now,
        can_authorize_provider=lambda provider: provider == ProviderKey.YOUTUBE.value,
        transaction_ttl=timedelta(seconds=5),
    )
    stop = threading.Event()

    def serve_control_queue() -> None:
        deadline = time.monotonic() + 5
        requests = control / "requests"
        while not stop.is_set() and time.monotonic() < deadline:
            if tuple(requests.glob("*.request")):
                drain_requests(tmp_path, profile="Default")
            time.sleep(0.01)

    with ThreadPoolExecutor(max_workers=1) as pool:
        agent = pool.submit(serve_control_queue)
        try:
            transaction = await service.begin(USER_ID, ProviderKey.YOUTUBE.value)
            result = transaction
            while result.status == ProviderAuthorizationStatus.PENDING:
                result = await service.get(USER_ID, transaction.transaction_id)
                await asyncio.sleep(0.01)
            assert result.status == ProviderAuthorizationStatus.SOURCE_AVAILABLE
        finally:
            stop.set()
            agent.result(timeout=1)
            await service.close()


@pytest.mark.asyncio
async def test_unsupported_provider_does_not_enqueue_authorization(
    postgres_engine: AsyncEngine,
    tmp_path: Path,
) -> None:
    service, repository = _service(
        postgres_engine,
        tmp_path,
        datetime(2026, 9, 20, 12, tzinfo=UTC),
    )

    with pytest.raises(ProviderAuthorizationError) as error:
        await service.begin(USER_ID, ProviderKey.QQVIDEO.value)
    assert error.value.code == "provider_unsupported"
    assert await repository.pending() == ()
    await service.close()


async def test_pending_record_recovers_a_crash_before_queue_publication(
    postgres_engine: AsyncEngine,
    tmp_path: Path,
) -> None:
    now = datetime.now(UTC)
    service, repository = _service(postgres_engine, tmp_path, now)
    record, created = await repository.accept(
        USER_ID,
        "youtube",
        ProviderAuthorizationSource.CURRENT_CHROME,
        now=now,
        ttl=timedelta(minutes=5),
        retention=timedelta(hours=24),
    )
    assert created
    request = tmp_path / "control" / "requests" / f"{record.id.hex}.request"
    assert not request.exists()
    await service.reconcile()
    first = request.read_bytes()
    await service.reconcile()
    assert request.read_bytes() == first
    await service.cancel(USER_ID, record.id.hex)
    await service.close()


async def test_many_api_replicas_admit_one_source_operation(
    postgres_engine: AsyncEngine,
    tmp_path: Path,
) -> None:
    now = datetime.now(UTC)
    services = [_service(postgres_engine, tmp_path, now)[0] for _ in range(10)]
    results = await asyncio.gather(
        *(service.begin(USER_ID, "youtube") for service in services)
    )
    assert len({result.transaction_id for result in results}) == 1
    assert len(tuple((tmp_path / "control" / "requests").glob("*.request"))) == 1
    for service in services:
        await service.close()


async def test_cancellation_fences_stale_completion_and_queue_republication(
    postgres_engine: AsyncEngine,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services.provider_authorization import ProviderAuthorizationRequest
    from app.workers.runner import provider_cookie_agent as agent

    now = datetime.now(UTC)
    service, repository = _service(postgres_engine, tmp_path, now)
    transaction = await service.begin(USER_ID, "youtube")
    stale = await repository.get(UUID(hex=transaction.transaction_id), USER_ID, now=now)
    await service.cancel(USER_ID, transaction.transaction_id)
    late = await repository.transition(
        stale, ProviderAuthorizationStatus.SOURCE_AVAILABLE, now=now
    )
    assert late.status == ProviderAuthorizationStatus.CANCELLED
    monkeypatch.setattr(
        agent, "_export_from_source", lambda *_a, **_kw: pytest.fail("cancelled export")
    )
    agent.drain_authorization_requests(tmp_path, profile="Default", browser_root=None)
    queue = FileProviderAuthorizationQueue(tmp_path, probe_timeout_seconds=0)
    queue.write_request(
        transaction.transaction_id,
        ProviderAuthorizationRequest(
            ProviderKey.YOUTUBE,
            transaction.expires_at,
            ProviderAuthorizationSource.CURRENT_CHROME,
        ),
    )
    assert not tuple((tmp_path / "control" / "requests").glob("*.request"))
    assert (
        tmp_path / "control" / "cancelled" / f"{transaction.transaction_id}.cancel"
    ).exists()


async def test_background_lifecycle_completes_without_a_browser_poll(
    postgres_engine: AsyncEngine,
    tmp_path: Path,
) -> None:
    now = datetime.now(UTC)
    service, repository = _service(postgres_engine, tmp_path, now)
    transaction = await service.begin(USER_ID, "youtube")
    response = (
        tmp_path / "control" / "responses" / f"{transaction.transaction_id}.response"
    )
    response.write_bytes(b"source_available\n")
    await service.start()
    first_task = service._task
    await service.start()
    assert service._task is first_task
    try:
        async with asyncio.timeout(3):
            while (
                await repository.get(
                    UUID(hex=transaction.transaction_id), USER_ID, now=now
                )
            ).status == ProviderAuthorizationStatus.PENDING:
                await asyncio.sleep(0.01)
    finally:
        await service.close()
    assert first_task.done()
    assert service._task is None


async def test_retention_cleanup_removes_only_terminal_owned_queue_entries(
    postgres_engine: AsyncEngine,
    tmp_path: Path,
) -> None:
    current = [datetime.now(UTC)]
    service, repository = _service(postgres_engine, tmp_path, lambda: current[0])
    transaction = await service.begin(USER_ID, "youtube")
    await service.cancel(USER_ID, transaction.transaction_id)
    current[0] = transaction.expires_at + timedelta(hours=24)
    other = await service.begin(OTHER_USER_ID, "douyin")
    await service.reconcile()
    for folder in ("requests", "responses", "cancelled"):
        assert not tuple(
            (tmp_path / "control" / folder).glob(f"{transaction.transaction_id}.*")
        )
    with pytest.raises(ProviderAuthorizationError):
        await repository.get(
            UUID(hex=transaction.transaction_id), USER_ID, now=current[0]
        )
    assert (
        tmp_path / "control" / "requests" / f"{other.transaction_id}.request"
    ).exists()


async def test_authorization_schema_bootstrap_and_repeat_preserve_terminal_state() -> (
    None
):
    from sqlalchemy import text
    from tests.postgres import isolated_postgres_engine

    sql = (Path(__file__).resolve().parents[2] / "sql/schema.sql").read_text()
    async with isolated_postgres_engine() as engine:
        async with engine.connect() as connection:
            schema = await connection.scalar(text("SELECT current_schema()"))
            assert schema.startswith("test_") and schema.replace("_", "").isalnum()
            await connection.execute(text(f'SET search_path TO "{schema}", public'))
            await connection.commit()
            raw = await connection.get_raw_connection()
            driver = raw.driver_connection
            await driver.execute(sql)
            await driver.execute("""
                INSERT INTO provider_authorizations VALUES (
                    '11111111-1111-4111-8111-111111111111',
                    '22222222-2222-4222-8222-222222222222', 'youtube',
                    'current_chrome', 'maintain_deployment_source', 'cancelled',
                    now() + interval '5 minutes', now() + interval '1 day', now(), now()
                )
            """)
            await driver.execute(sql)
            row = await driver.fetchrow("SELECT * FROM provider_authorizations")
            assert row["status"] == "cancelled"
            assert row["purpose"] == "maintain_deployment_source"
