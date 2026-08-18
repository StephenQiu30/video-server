from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from app.infrastructure.analysis_report_lifecycle import ReportPurgeResult
from app.infrastructure.object_storage import StoredObject
from app.workers.report.lifecycle import ReportLifecycleWorker

NOW = datetime(2026, 8, 10, 13, tzinfo=UTC)


class Repository:
    async def purge_report_artifacts(self, now, delete, *, limit):
        await delete("analyses/retired/report.md")
        return ReportPurgeResult(1, 0)

    async def expected_report_object_keys(self):
        return frozenset({"analyses/expected/report.md"})


class Storage:
    def __init__(self) -> None:
        self.deleted: list[str] = []

    async def delete(self, key: str) -> None:
        self.deleted.append(key)

    async def list(self, prefix: str):
        assert prefix == "analyses/"
        return (
            StoredObject("analyses/expected/report.md", NOW - timedelta(days=1)),
            StoredObject("analyses/orphan/report.docx", NOW - timedelta(hours=2)),
            StoredObject("analyses/recent/report.md", NOW - timedelta(minutes=5)),
        )


@pytest.mark.asyncio
async def test_lifecycle_deletes_retired_artifacts_and_quarantined_orphans() -> None:
    storage = Storage()
    worker = ReportLifecycleWorker(
        Repository(),
        storage,
        lambda: NOW,
        interval=60,
        batch_size=10,
        orphan_grace=timedelta(hours=1),
        delete_timeout=1,
    )

    result = await worker.tick()

    assert result.artifacts == ReportPurgeResult(1, 0)
    assert result.orphans_deleted == 1
    assert storage.deleted == [
        "analyses/retired/report.md",
        "analyses/orphan/report.docx",
    ]
