from __future__ import annotations

from datetime import UTC, datetime

import pytest
from app.infrastructure.database import ArtifactPurgeResult
from app.workers.download.artifacts import (
    ArtifactCleanupSettings,
    ArtifactGarbageCollector,
)


class FakeRepository:
    def __init__(self) -> None:
        self.calls: list[tuple[datetime, int]] = []

    async def purge_expired_artifacts(self, now, delete, *, limit):
        self.calls.append((now, limit))
        await delete("downloads/job/1/video.mp4")
        return ArtifactPurgeResult(deleted=1, failed=0)


@pytest.mark.asyncio
async def test_artifact_gc_deletes_with_timeout() -> None:
    repository = FakeRepository()
    deleted: list[str] = []
    now = datetime(2026, 8, 8, tzinfo=UTC)
    collector = ArtifactGarbageCollector(
        repository,
        lambda key: _record(deleted, key),
        lambda: now,
        ArtifactCleanupSettings(interval=5, batch_size=2, delete_timeout=1),
    )

    result = await collector.tick()

    assert result == ArtifactPurgeResult(deleted=1, failed=0)
    assert deleted == ["downloads/job/1/video.mp4"]
    assert repository.calls == [(now, 2)]


async def _record(deleted: list[str], key: str) -> None:
    deleted.append(key)
