from __future__ import annotations

import hashlib
from pathlib import Path
from uuid import uuid4

import pytest
from app.application.analysis_execution import (
    AnalysisArtifactError,
    AnalysisArtifactSource,
)
from app.workers.analysis.artifacts import LocalAnalysisArtifactLoader


class FakeStorage:
    def __init__(self, content: bytes) -> None:
        self.content = content

    async def download(self, object_key: str, target: Path) -> None:
        target.write_bytes(self.content)


def source(content: bytes, *, sha256: str | None = None) -> AnalysisArtifactSource:
    return AnalysisArtifactSource(
        artifact_id=uuid4(),
        bucket="video-artifacts",
        object_key="downloads/job/1/video.mp4",
        sha256=sha256 or hashlib.sha256(content).hexdigest(),
        size_bytes=len(content),
        container="mp4",
    )


@pytest.mark.asyncio
async def test_loader_verifies_source_and_removes_success_or_failure_workspaces(
    tmp_path: Path,
) -> None:
    content = b"controlled-media"
    loader = LocalAnalysisArtifactLoader(
        FakeStorage(content),
        workspace_root=tmp_path / "analysis-work",
        bucket="video-artifacts",
        max_source_bytes=1024,
    )
    await loader.prepare_root()

    local = await loader.materialize(source(content), job_id=uuid4(), attempt=1)
    assert local.artifact.read_bytes() == content
    await loader.cleanup(local)
    assert not local.workspace.exists()

    with pytest.raises(AnalysisArtifactError, match="artifact_integrity_failed"):
        await loader.materialize(
            source(content, sha256="0" * 64), job_id=uuid4(), attempt=1
        )
    assert list((tmp_path / "analysis-work").iterdir()) == []
