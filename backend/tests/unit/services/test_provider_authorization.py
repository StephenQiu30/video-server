from __future__ import annotations

import asyncio
import shutil
import socket
import subprocess
import threading
import time
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import pytest
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
from redis.asyncio import Redis

USER_ID = UUID("11111111-1111-4111-8111-111111111111")
OTHER_USER_ID = UUID("22222222-2222-4222-8222-222222222222")


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture
def redis_url(tmp_path: Path) -> Iterator[str]:
    redis_server = shutil.which("redis-server")
    redis_cli = shutil.which("redis-cli")
    if redis_server is None or redis_cli is None:
        pytest.skip("redis-server and redis-cli are required")
    port = _free_port()
    process = subprocess.Popen(
        [
            redis_server,
            "--bind",
            "127.0.0.1",
            "--port",
            str(port),
            "--save",
            "",
            "--appendonly",
            "no",
            "--dir",
            str(tmp_path),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        deadline = time.monotonic() + 3
        while True:
            result = subprocess.run(
                [redis_cli, "-h", "127.0.0.1", "-p", str(port), "ping"],
                capture_output=True,
                check=False,
            )
            if result.stdout.strip() == b"PONG":
                break
            if time.monotonic() >= deadline:
                pytest.fail("redis-server did not become ready")
            time.sleep(0.02)
        yield f"redis://127.0.0.1:{port}/0"
    finally:
        process.terminate()
        process.wait(timeout=3)


class FakeRedis:
    def __init__(self) -> None:
        self.hashes: dict[str, dict[str, str]] = {}
        self.strings: dict[str, str] = {}

    async def hset(
        self,
        key: str,
        field: str | None = None,
        value: str | None = None,
        *,
        mapping: dict[str, str] | None = None,
    ) -> int:
        record = self.hashes.setdefault(key, {})
        if mapping is not None:
            record.update(mapping)
            return len(mapping)
        if field is None or value is None:
            raise AssertionError("invalid fake Redis hset call")
        record[field] = value
        return 1

    async def expire(self, _key: str, _ttl: int) -> bool:
        return True

    async def eval(
        self,
        script: str,
        _number_of_keys: int,
        key: str,
        *arguments: str | int,
    ) -> int | str:
        if "KEYS[2]" in script:
            record_key = str(arguments[0])
            values = arguments[1:]
            token = str(values[0])
            if key in self.strings:
                return self.strings[key]
            self.strings[key] = token
            self.hashes[record_key] = {
                "user_id": str(values[2]),
                "provider_key": str(values[3]),
                "source": str(values[4]),
                "status": str(values[5]),
                "expires_at": str(values[6]),
                "active_key": key,
            }
            return token
        if "HGET" not in script:
            token = str(arguments[0])
            if self.strings.get(key) != token:
                return 0
            self.strings.pop(key, None)
            return 1
        expected, target, _retention = arguments
        record = self.hashes.get(key)
        if record is None or record.get("status") != str(expected):
            return 0
        record["status"] = str(target)
        return 1

    async def set(
        self,
        key: str,
        value: str,
        *,
        ex: int,
        nx: bool,
    ) -> bool:
        del ex
        if nx and key in self.strings:
            return False
        self.strings[key] = value
        return True

    async def get(self, key: str) -> str | None:
        return self.strings.get(key)

    async def hgetall(self, key: str) -> dict[str, str]:
        return dict(self.hashes.get(key, {}))

    async def delete(self, key: str) -> int:
        return int(self.hashes.pop(key, None) is not None)

    async def aclose(self) -> None:
        return None


def _service(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    now: datetime | Callable[[], datetime],
) -> tuple[ProviderAuthorizationService, FakeRedis]:
    fake = FakeRedis()
    monkeypatch.setattr(
        "app.services.provider_authorization.Redis.from_url",
        lambda _url, decode_responses: fake,
    )
    control = authorization_runtime(tmp_path)
    prepare_authorization_runtime(tmp_path)
    (control / AUTHORIZATION_READY_MARKER).write_bytes(AUTHORIZATION_READY_PAYLOAD)
    clock = now if callable(now) else lambda: now
    service = ProviderAuthorizationService(
        FileProviderAuthorizationQueue(tmp_path, probe_timeout_seconds=0),
        "redis://test/0",
        now=clock,
        can_authorize_provider=lambda provider: (
            provider in {ProviderKey.YOUTUBE.value, ProviderKey.DOUYIN.value}
        ),
        transaction_ttl=timedelta(minutes=5),
    )
    return service, fake


@pytest.mark.asyncio
async def test_begin_and_poll_authorization_without_cookie_material(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    now = datetime(2026, 9, 20, 12, tzinfo=UTC)
    service, _redis = _service(monkeypatch, tmp_path, now)

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
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    service, _redis = _service(
        monkeypatch,
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
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    service, _redis = _service(
        monkeypatch,
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
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    service, _redis = _service(
        monkeypatch,
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
    tmp_path: Path,
) -> None:
    service, redis = _service(
        monkeypatch,
        tmp_path,
        datetime(2026, 9, 20, 12, tzinfo=UTC),
    )
    transaction = await service.begin(USER_ID, ProviderKey.YOUTUBE.value)
    response_path = (
        tmp_path / "control" / "responses" / f"{transaction.transaction_id}.response"
    )
    response_path.write_bytes(b"source_available\n")

    async def fail_transition(*_args: object) -> int:
        raise ConnectionError("simulated Redis failure")

    monkeypatch.setattr(redis, "eval", fail_transition)
    with pytest.raises(ConnectionError, match="simulated Redis failure"):
        await service.get(USER_ID, transaction.transaction_id)

    assert response_path.exists()
    await service.close()


@pytest.mark.asyncio
async def test_deadline_wins_over_a_late_authorization_response(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    current = [datetime(2026, 9, 20, 12, tzinfo=UTC)]
    service, _redis = _service(monkeypatch, tmp_path, lambda: current[0])
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
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    service, _redis = _service(
        monkeypatch,
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
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    service, _redis = _service(
        monkeypatch,
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
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    service, _redis = _service(
        monkeypatch,
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


@pytest.mark.asyncio
async def test_real_redis_separates_operation_deadline_from_result_retention(
    tmp_path: Path,
    redis_url: str,
) -> None:
    now = datetime(2026, 9, 20, 12, tzinfo=UTC)
    control = authorization_runtime(tmp_path)
    prepare_authorization_runtime(tmp_path)
    (control / AUTHORIZATION_READY_MARKER).write_bytes(AUTHORIZATION_READY_PAYLOAD)
    service = ProviderAuthorizationService(
        FileProviderAuthorizationQueue(tmp_path, probe_timeout_seconds=0),
        redis_url,
        now=lambda: now,
        can_authorize_provider=lambda provider: provider == ProviderKey.YOUTUBE.value,
        transaction_ttl=timedelta(seconds=5),
        result_retention=timedelta(seconds=30),
    )
    client = Redis.from_url(redis_url, decode_responses=True)
    try:
        transaction = await service.begin(USER_ID, ProviderKey.YOUTUBE.value)
        record_key = service._key(transaction.transaction_id)
        record = await client.hgetall(record_key)
        active_key = record["active_key"]

        assert 1 <= await client.ttl(active_key) <= 5
        assert 30 < await client.ttl(record_key) <= 35

        response_path = (
            tmp_path
            / "control"
            / "responses"
            / f"{transaction.transaction_id}.response"
        )
        response_path.write_bytes(b"source_available\n")
        result = await service.get(USER_ID, transaction.transaction_id)

        assert result.status == ProviderAuthorizationStatus.SOURCE_AVAILABLE
        assert await client.get(active_key) is None
        assert 1 <= await client.ttl(record_key) <= 30
    finally:
        await client.aclose()
        await service.close()


@pytest.mark.asyncio
async def test_real_redis_and_agent_complete_the_authorization_control_loop(
    tmp_path: Path,
    redis_url: str,
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
        redis_url,
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
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    service, redis = _service(
        monkeypatch,
        tmp_path,
        datetime(2026, 9, 20, 12, tzinfo=UTC),
    )

    with pytest.raises(ProviderAuthorizationError) as error:
        await service.begin(USER_ID, ProviderKey.QQVIDEO.value)
    assert error.value.code == "provider_unsupported"
    assert redis.hashes == {}
    await service.close()
