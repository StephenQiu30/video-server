from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

import pytest
from app.application.import_execution import ImportWorkspace
from app.workers.imports.thumbnail_backfill import DownloadThumbnailBackfill

JOB_ID = UUID("11111111-1111-4111-8111-111111111111")


@dataclass(frozen=True)
class Candidate:
    job_id: UUID
    owner_hash: str
    object_key: str


class Repository:
    async def list_missing_download_thumbnails(self, *, limit: int):
        assert limit == 10
        return (Candidate(JOB_ID, "a" * 64, f"downloads/{JOB_ID}/1/video.mp4"),)


class Storage:
    async def download(self, object_key: str, target: Path) -> None:
        assert object_key == f"downloads/{JOB_ID}/1/video.mp4"
        target.write_bytes(b"verified video")


class Workspace:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.cleaned: list[Path | None] = []

    async def create(self, task_id: str) -> ImportWorkspace:
        assert task_id == f"import_{JOB_ID.hex}_1"
        path = self.root / task_id
        path.mkdir()
        return ImportWorkspace(path=path, input_path=path / "video.mp4")

    async def cleanup(self, task_id: str, workspace: Path | None) -> None:
        self.cleaned.append(workspace)


class Recovery:
    def __init__(self) -> None:
        self.calls: list[tuple[UUID, str, Path]] = []

    async def recover(
        self, resource_id: UUID, owner_hash: str, artifact: Path
    ) -> bool:
        self.calls.append((resource_id, owner_hash, artifact))
        return True


@pytest.mark.asyncio
async def test_backfills_a_missing_local_video_cover(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path)
    recovery = Recovery()
    backfill = DownloadThumbnailBackfill(
        Repository(),
        Storage(),
        workspace,
        recovery,
        interval=5,
        batch_size=10,
    )

    recovered = await backfill.tick()

    assert recovered == 1
    assert recovery.calls[0][0:2] == (JOB_ID, "a" * 64)
    assert recovery.calls[0][2].read_bytes() == b"verified video"
    assert len(workspace.cleaned) == 1
