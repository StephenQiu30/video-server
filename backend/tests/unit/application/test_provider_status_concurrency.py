import asyncio
from datetime import UTC, datetime

import pytest
from app.services.provider_canaries import ProviderStatusService


class Evidence:
    def __init__(self):
        self.calls = 0
        self.failure = False

    async def list_recent(self, **kwargs):
        self.calls += 1
        if self.failure:
            raise RuntimeError("database unavailable")
        return {}


class Contexts:
    def __init__(self):
        self.calls = 0

    async def contexts_for_providers(self, requested):
        self.calls += 1
        return {}


async def test_two_hundred_readers_share_one_snapshot_and_expiry_refresh():
    evidence, contexts = Evidence(), Contexts()
    clock = [0.0]
    service = ProviderStatusService(
        evidence,
        (),
        now=lambda: datetime.now(UTC),
        context_reader=contexts,
        snapshot_ttl_seconds=30,
        monotonic=lambda: clock[0],
    )
    results = await asyncio.gather(*(service.list() for _ in range(200)))
    assert results == [()] * 200
    assert evidence.calls == 1
    clock[0] = 29.99
    await service.list()
    assert evidence.calls == 1
    clock[0] = 30
    await asyncio.gather(*(service.list() for _ in range(200)))
    assert evidence.calls == 2


async def test_failed_refresh_never_serves_expired_snapshot_or_poisoned_lock():
    evidence, contexts = Evidence(), Contexts()
    clock = [0.0]
    service = ProviderStatusService(
        evidence,
        (),
        now=lambda: datetime.now(UTC),
        context_reader=contexts,
        snapshot_ttl_seconds=30,
        monotonic=lambda: clock[0],
    )
    await service.list()
    clock[0] = 31
    evidence.failure = True
    with pytest.raises(RuntimeError, match="database unavailable"):
        await service.list()
    evidence.failure = False
    assert await service.list() == ()
    assert evidence.calls == 3


async def test_contended_refresh_and_cancellation_release_the_single_flight():
    started, release = asyncio.Event(), asyncio.Event()

    class SlowEvidence(Evidence):
        async def list_recent(self, **kwargs):
            self.calls += 1
            started.set()
            await release.wait()
            return {}

    evidence = SlowEvidence()
    service = ProviderStatusService(
        evidence,
        (),
        now=lambda: datetime.now(UTC),
        context_reader=Contexts(),
        snapshot_ttl_seconds=30,
    )
    first = asyncio.create_task(service.list())
    await started.wait()
    readers = [asyncio.create_task(service.list()) for _ in range(199)]
    await asyncio.sleep(0)
    assert evidence.calls == 1
    first.cancel()
    with pytest.raises(asyncio.CancelledError):
        await first
    release.set()
    assert await asyncio.gather(*readers) == [()] * 199
    assert evidence.calls == 2


@pytest.mark.parametrize("ttl", [-1, 31, float("nan"), float("inf")])
def test_cache_cannot_outlive_the_published_thirty_second_bound(ttl):
    with pytest.raises(ValueError):
        ProviderStatusService(
            Evidence(),
            (),
            now=lambda: datetime.now(UTC),
            context_reader=Contexts(),
            snapshot_ttl_seconds=ttl,
        )
