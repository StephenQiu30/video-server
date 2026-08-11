from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from app.workers.download.sweeper import DownloadRecoverySweeper
from app.workers.download.workspace import SharedWorkspaceCleaner


class FakeRecoveryRepository:
    def __init__(self) -> None:
        self.queued = (uuid4(),)
        self.stale = (uuid4(),)
        self.ready = (uuid4(),)
        self.calls: list[str] = []

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
