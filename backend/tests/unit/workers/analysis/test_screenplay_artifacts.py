from __future__ import annotations

import hashlib
import os
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from app.application.analysis_execution import (
    AnalysisArtifactError,
    AnalysisScreenplaySource,
    ScreenplaySceneSource,
)
from app.workers.analysis.screenplay_artifacts import LocalScreenplayArtifactLoader

DOCUMENT_ID = UUID("11111111-1111-4111-8111-111111111111")


class FakeStorage:
    def __init__(self, content: bytes) -> None:
        self.content = content

    async def download(self, object_key: str, target: Path) -> None:
        target.write_bytes(self.content)


def source(
    content: bytes,
    text: str,
    *,
    sha256: str | None = None,
    object_key: str | None = None,
) -> AnalysisScreenplaySource:
    boundary = text.index("\n") + 1
    return AnalysisScreenplaySource(
        artifact_id=uuid4(),
        document_id=DOCUMENT_ID,
        owner_hash="a" * 64,
        bucket="video-artifacts",
        object_key=(object_key or f"documents/{DOCUMENT_ID}/1/screenplay.md"),
        sha256=sha256 or hashlib.sha256(content).hexdigest(),
        size_bytes=len(content),
        character_count=len(text),
        detected_language="mixed",
        scenes=(
            ScreenplaySceneSource("scene-0001", 0, boundary),
            ScreenplaySceneSource("scene-0002", boundary, len(text)),
        ),
    )


def loader(tmp_path: Path, content: bytes) -> LocalScreenplayArtifactLoader:
    return LocalScreenplayArtifactLoader(
        FakeStorage(content),
        workspace_root=tmp_path / "analysis-work",
        bucket="video-artifacts",
        max_source_bytes=1024,
    )


@pytest.mark.asyncio
async def test_screenplay_loader_verifies_utf8_hash_ranges_and_cleanup(
    tmp_path: Path,
) -> None:
    text = "INT. ROOM - DAY\n内景 房间 日\n"
    content = text.encode()
    artifact_loader = loader(tmp_path, content)
    await artifact_loader.prepare_root()

    local = await artifact_loader.materialize(
        source(content, text), job_id=uuid4(), attempt=1
    )

    assert local.screenplay.read_text(encoding="utf-8") == text
    assert local.screenplay == local.workspace / "input" / "screenplay.md"
    if os.name == "posix":
        assert local.screenplay.stat().st_mode & 0o777 == 0o400
    await artifact_loader.cleanup(local)
    assert not local.workspace.exists()


@pytest.mark.asyncio
async def test_screenplay_loader_rejects_integrity_and_key_failures(
    tmp_path: Path,
) -> None:
    text = "INT. ROOM - DAY\n内景 房间 日\n"
    content = text.encode()
    artifact_loader = loader(tmp_path, content)

    with pytest.raises(AnalysisArtifactError, match="artifact_integrity_failed"):
        await artifact_loader.materialize(
            source(content, text, sha256="0" * 64), job_id=uuid4(), attempt=1
        )
    with pytest.raises(AnalysisArtifactError, match="input_artifact_unavailable"):
        await artifact_loader.materialize(
            source(content, text, object_key="documents/other/1/screenplay.md"),
            job_id=uuid4(),
            attempt=1,
        )

    assert list((tmp_path / "analysis-work").iterdir()) == []
