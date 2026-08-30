from __future__ import annotations

import asyncio
import threading
from pathlib import Path

import pytest
from app.runner.provider_cookie_sync import ProviderCookieSyncClient
from app.runner.youtube_cookie_sync import OK, SyncResult, drain_requests

TOKEN = "d" * 32


async def test_client_cancellation_after_host_snapshot_leaves_no_orphan(
    tmp_path: Path,
) -> None:
    runtime = tmp_path / "runtime"
    requests = runtime / "requests"
    responses = runtime / "responses"
    requests.mkdir(parents=True)
    responses.mkdir()
    client = ProviderCookieSyncClient(
        runtime,
        poll_interval_seconds=0.001,
        token_factory=lambda: TOKEN,
    )
    refresh_started = threading.Event()
    release_refresh = threading.Event()

    def refresh() -> SyncResult:
        refresh_started.set()
        if not release_refresh.wait(timeout=1):
            raise AssertionError("test did not release host refresh")
        return OK

    client_task = asyncio.create_task(client.sync())
    await _wait_for_request(requests / f"{TOKEN}.request")
    host_task = asyncio.create_task(
        asyncio.to_thread(
            drain_requests,
            runtime,
            tmp_path / "secret",
            refresh=refresh,
        )
    )
    assert await asyncio.to_thread(refresh_started.wait, 1)
    client_task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await client_task
    release_refresh.set()
    await host_task

    assert not tuple(requests.iterdir())
    assert not tuple(responses.iterdir())


async def _wait_for_request(request: Path) -> None:
    async with asyncio.timeout(1):
        while not request.exists():
            await asyncio.sleep(0.001)
