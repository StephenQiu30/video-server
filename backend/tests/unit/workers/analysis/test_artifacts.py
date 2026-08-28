from __future__ import annotations

import hashlib
import os
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
        duration_ms=1_000,
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
    assert local.artifact == local.workspace / "input" / "video.bin"
    if os.name == "posix":
        assert local.artifact.stat().st_mode & 0o777 == 0o400
    await loader.cleanup(local)
    assert not local.workspace.exists()

    with pytest.raises(AnalysisArtifactError, match="artifact_integrity_failed"):
        await loader.materialize(
            source(content, sha256="0" * 64), job_id=uuid4(), attempt=1
        )
    assert list((tmp_path / "analysis-work").iterdir()) == []


@pytest.mark.asyncio
async def test_loader_rejects_workspace_below_agent_instructions(
    tmp_path: Path,
) -> None:
    governed = tmp_path / "repository"
    governed.mkdir()
    (governed / "AGENTS.md").write_text("# controlled instructions\n")
    loader = LocalAnalysisArtifactLoader(
        FakeStorage(b"controlled-media"),
        workspace_root=governed / "tmp" / "analysis-work",
        bucket="video-artifacts",
        max_source_bytes=1024,
    )

    with pytest.raises(AnalysisArtifactError) as raised:
        await loader.prepare_root()

    assert raised.value.code == "analysis_sandbox_unavailable"
    assert not (governed / "tmp").exists()


@pytest.mark.asyncio
async def test_loader_rejects_agent_instructions_in_workspace_root(
    tmp_path: Path,
) -> None:
    workspace_root = tmp_path / "analysis-work"
    workspace_root.mkdir()
    (workspace_root / "AGENTS.md").write_text("# controlled instructions\n")
    loader = LocalAnalysisArtifactLoader(
        FakeStorage(b"controlled-media"),
        workspace_root=workspace_root,
        bucket="video-artifacts",
        max_source_bytes=1024,
    )

    with pytest.raises(AnalysisArtifactError) as raised:
        await loader.prepare_root()

    assert raised.value.code == "analysis_sandbox_unavailable"


@pytest.mark.asyncio
async def test_loader_resolves_symlinked_workspace_ancestors(tmp_path: Path) -> None:
    governed = tmp_path / "repository"
    governed.mkdir()
    (governed / "AGENTS.md").write_text("# controlled instructions\n")
    alias = tmp_path / "workspace-alias"
    try:
        alias.symlink_to(governed, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlinks are unavailable")
    loader = LocalAnalysisArtifactLoader(
        FakeStorage(b"controlled-media"),
        workspace_root=alias / "analysis-work",
        bucket="video-artifacts",
        max_source_bytes=1024,
    )

    with pytest.raises(AnalysisArtifactError) as raised:
        await loader.prepare_root()

    assert raised.value.code == "analysis_sandbox_unavailable"
    assert not (governed / "analysis-work").exists()
