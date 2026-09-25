import asyncio
from datetime import UTC, datetime, timedelta

from app.workers.outbox.operation_log_retention import OperationLogRetention

NOW = datetime(2026, 9, 25, tzinfo=UTC)


class _Store:
    def __init__(self, batches: list[int]) -> None:
        self.batches = batches
        self.calls: list[tuple[datetime, int]] = []

    async def purge_before(self, cutoff: datetime, *, limit: int) -> int:
        self.calls.append((cutoff, limit))
        return self.batches.pop(0) if self.batches else 0


def _retention(store: _Store, **kwargs: object) -> OperationLogRetention:
    return OperationLogRetention(
        store,
        clock=lambda: NOW,
        retention=timedelta(days=180),
        interval=60,
        batch_size=100,
        **kwargs,  # type: ignore[arg-type]
    )


async def test_tick_drains_full_batches_until_a_short_one() -> None:
    store = _Store([100, 100, 7, 100])
    assert await _retention(store).tick() == 207
    assert store.calls == [(NOW - timedelta(days=180), 100)] * 3


async def test_tick_bounds_work_per_sweep() -> None:
    store = _Store([100] * 10)
    assert await _retention(store, max_batches=3).tick() == 300
    assert len(store.calls) == 3


async def test_run_survives_failures_and_stops_promptly() -> None:
    class Failing(_Store):
        async def purge_before(self, cutoff: datetime, *, limit: int) -> int:
            self.calls.append((cutoff, limit))
            raise RuntimeError("database unavailable")

    store = Failing([])
    stop = asyncio.Event()
    task = asyncio.create_task(_retention(store).run(stop))
    await asyncio.sleep(0)
    stop.set()
    await asyncio.wait_for(task, 1)
    assert len(store.calls) == 1
