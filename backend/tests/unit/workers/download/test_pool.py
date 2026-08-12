from __future__ import annotations

import asyncio

import pytest
from app.workers.download.pool import AsyncWorkerPool


@pytest.mark.asyncio
async def test_pool_runs_jobs_concurrently_with_fixed_worker_count() -> None:
    active = 0
    peak = 0
    started = asyncio.Event()
    release = asyncio.Event()

    async def process(_: int) -> None:
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        if active == 2:
            started.set()
        await release.wait()
        active -= 1

    pool = AsyncWorkerPool(process, workers=2)
    await pool.start()
    submissions = [asyncio.create_task(pool.submit(item)) for item in range(4)]

    await asyncio.wait_for(started.wait(), timeout=1)
    assert peak == 2
    release.set()
    await asyncio.gather(*submissions)
    await pool.close()


@pytest.mark.asyncio
async def test_pool_rejects_submissions_after_close() -> None:
    pool = AsyncWorkerPool(lambda _: asyncio.sleep(0), workers=1)
    await pool.start()
    await pool.close()

    with pytest.raises(RuntimeError, match="not accepting"):
        await pool.submit(1)


@pytest.mark.asyncio
async def test_pool_close_is_bounded_when_processor_hangs() -> None:
    started = asyncio.Event()
    hung = asyncio.Event()

    async def hang(_: int) -> None:
        started.set()
        await hung.wait()

    pool = AsyncWorkerPool(hang, workers=1, drain_timeout=0.05)
    await pool.start()
    await pool.submit(1)
    await started.wait()

    # close() must not wait for the hung processor forever; a stalled delivery
    # stays unacked and is requeued by RabbitMQ when the channel closes.
    await asyncio.wait_for(pool.close(), timeout=2)


@pytest.mark.asyncio
async def test_pool_close_drains_in_flight_jobs_within_timeout() -> None:
    release = asyncio.Event()
    completed: list[int] = []

    async def process(item: int) -> None:
        await release.wait()
        completed.append(item)

    pool = AsyncWorkerPool(process, workers=1, drain_timeout=2)
    await pool.start()
    await pool.submit(7)
    await asyncio.sleep(0)
    release.set()
    await asyncio.wait_for(pool.close(), timeout=2)

    assert completed == [7]
