from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from app.workers.download.thumbnail import ArtifactThumbnailRecovery


class FakePersist:
    def __init__(self) -> None:
        self.calls: list[tuple[object, str, str | None]] = []

    async def __call__(
        self, inspection_id: object, owner_hash: str, data_url: str | None
    ) -> bool:
        self.calls.append((inspection_id, owner_hash, data_url))
        return True


@pytest.mark.asyncio
async def test_extracts_and_persists_a_bounded_jpeg(tmp_path: Path) -> None:
    artifact = tmp_path / "video.mp4"
    artifact.write_bytes(b"verified video")
    persist = FakePersist()
    commands: list[tuple[str, ...]] = []

    async def run(command: tuple[str, ...], timeout: float) -> bool:
        commands.append(command)
        assert timeout == 12
        Path(command[-1]).write_bytes(b"\xff\xd8\xffcontrolled-jpeg")
        return True

    recovery = ArtifactThumbnailRecovery(
        persist,
        ffmpeg_binary=Path("ffmpeg"),
        timeout_seconds=12,
        max_bytes=1024,
        run_process=run,
    )
    inspection_id = uuid4()

    recovered = await recovery.recover(inspection_id, "a" * 64, artifact)

    assert recovered is True
    assert persist.calls[0][:2] == (inspection_id, "a" * 64)
    assert persist.calls[0][2] == (
        "data:image/jpeg;base64,/9j/Y29udHJvbGxlZC1qcGVn"
    )
    assert "-protocol_whitelist" in commands[0]
    assert commands[0][commands[0].index("-protocol_whitelist") + 1] == (
        "file,crypto,data"
    )
    assert list(tmp_path.glob(".thumbnail-*.jpg")) == []


@pytest.mark.asyncio
async def test_rejects_invalid_extracted_content_without_persisting(
    tmp_path: Path,
) -> None:
    artifact = tmp_path / "video.mp4"
    artifact.write_bytes(b"verified video")
    persist = FakePersist()

    async def run(command: tuple[str, ...], _: float) -> bool:
        Path(command[-1]).write_bytes(b"not-a-jpeg")
        return True

    recovery = ArtifactThumbnailRecovery(
        persist,
        ffmpeg_binary=Path("ffmpeg"),
        timeout_seconds=12,
        max_bytes=1024,
        run_process=run,
    )

    recovered = await recovery.recover(uuid4(), "a" * 64, artifact)

    assert recovered is False
    assert persist.calls == []
    assert list(tmp_path.glob(".thumbnail-*.jpg")) == []
