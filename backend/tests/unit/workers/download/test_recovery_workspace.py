from __future__ import annotations

import asyncio
import logging
import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from app.workers.download.sweeper import DownloadRecoverySweeper, RecoverySettings
from app.workers.download.workspace import SharedWorkspaceCleaner


class FakeRecoveryRepository:
    def __init__(self) -> None:
        self.queued = (uuid4(),)
        self.stale = (uuid4(),)
        self.ready = (uuid4(),)
        self.calls: list[str] = []
        self.active: frozenset[str] = frozenset()

    async def active_workspace_task_ids(self, now):
        return self.active

    async def recover_stale_queued(self, now, stale_before, *, limit=100):
        assert stale_before < now
        self.calls.append("queued")
        return self.queued

    async def reclaim_stale(self, now, *, limit=100):
        self.calls.append("stale")
        return self.stale

    async def release_ready_retries(self, now, *, limit=100):
        self.calls.append("ready")
        return self.ready


@pytest.mark.asyncio
async def test_recovery_republishes_queued_reclaims_stale_and_releases_retry() -> None:
    repository = FakeRecoveryRepository()
    sweeper = DownloadRecoverySweeper(
        repository, lambda: datetime(2026, 8, 6, tzinfo=UTC)
    )
    assert await sweeper.tick() == (
        repository.queued,
        repository.stale,
        repository.ready,
    )
    assert repository.calls == ["queued", "stale", "ready"]


@pytest.mark.asyncio
async def test_recovery_loop_logs_tick_failures(
    caplog: pytest.LogCaptureFixture,
) -> None:
    stop = asyncio.Event()

    class FailingRepository(FakeRecoveryRepository):
        async def recover_stale_queued(self, now, stale_before, *, limit=100):
            stop.set()
            raise RuntimeError("database unavailable")

    sweeper = DownloadRecoverySweeper(
        FailingRepository(),
        lambda: datetime(2026, 8, 6, tzinfo=UTC),
        RecoverySettings(interval=0.01),
    )

    with caplog.at_level(logging.ERROR):
        await sweeper.run(stop)

    assert "download recovery sweep failed" in caplog.text
    assert "database unavailable" in caplog.text


@pytest.mark.asyncio
async def test_cleanup_removes_only_matching_task_workspace(tmp_path) -> None:
    root = tmp_path / "work"
    root.mkdir()
    task_id = "download_abc_1"
    owned = root / f"{task_id}-controlled"
    owned.mkdir()
    (owned / "artifact.mp4").write_bytes(b"video")
    unrelated = root / "download_other_1-controlled"
    unrelated.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    link = root / f"{task_id}-link"
    link.symlink_to(outside, target_is_directory=True)

    await SharedWorkspaceCleaner(root).cleanup(task_id, owned)

    assert not owned.exists()
    assert not link.exists()
    assert unrelated.exists()
    assert outside.exists()


@pytest.mark.asyncio
async def test_recovery_collects_old_orphans_but_keeps_active_and_unrelated(
    tmp_path,
) -> None:
    root = tmp_path / "work"
    root.mkdir()
    now = datetime(2026, 8, 6, tzinfo=UTC)
    active_id = f"download_{uuid4().hex}_1"
    orphan_id = f"download_{uuid4().hex}_2"
    recent_id = f"download_{uuid4().hex}_3"
    active = root / f"{active_id}-active"
    orphan = root / f"{orphan_id}-orphan"
    recent = root / f"{recent_id}-recent"
    unrelated = root / "not-a-download-workspace"
    outside = tmp_path / "outside"
    outside.mkdir()
    link = root / f"{uuid4().hex}-link"

    for directory in (active, orphan, recent):
        directory.mkdir()
    old_timestamp = (now - timedelta(hours=2)).timestamp()
    os.utime(active, (old_timestamp, old_timestamp))
    os.utime(orphan, (old_timestamp, old_timestamp))
    recent_timestamp = (now - timedelta(minutes=10)).timestamp()
    os.utime(recent, (recent_timestamp, recent_timestamp))
    unrelated.mkdir()
    link.symlink_to(outside, target_is_directory=True)

    repository = FakeRecoveryRepository()
    repository.active = frozenset({active_id})
    sweeper = DownloadRecoverySweeper(
        repository,
        lambda: now,
        RecoverySettings(workspace_gc_after=timedelta(hours=1)),
        SharedWorkspaceCleaner(root),
    )

    await sweeper.tick()

    assert not orphan.exists()
    assert active.exists()
    assert recent.exists()
    assert unrelated.exists()
    assert link.is_symlink()
