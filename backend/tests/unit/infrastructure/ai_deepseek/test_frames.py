from __future__ import annotations

import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest
from app.infrastructure.ai_deepseek.config import DeepSeekAdapterConfig
from app.infrastructure.ai_deepseek.frames import DeepSeekFrameExtractor
from app.runner.process import ProcessResult


class FakeSupervisor:
    def __init__(self) -> None:
        self.argv: tuple[str, ...] = ()

    async def run(
        self,
        argv: Sequence[str],
        *,
        cwd: Path,
        timeout_seconds: float,
        env: Mapping[str, str] | None = None,
        input_bytes: bytes | None = None,
    ) -> ProcessResult:
        del timeout_seconds, env, input_bytes
        self.argv = tuple(argv)
        output = cwd / "work" / "deepseek-frames"
        (output / "frame-0001.jpg").write_bytes(b"one")
        (output / "frame-0002.jpg").write_bytes(b"two")
        return ProcessResult(0, b"", b"", False, False)


@pytest.mark.asyncio
async def test_ffmpeg_frames_are_bounded_and_timestamped(tmp_path: Path) -> None:
    executable = Path(sys.executable)
    config = DeepSeekAdapterConfig(
        model="deepseek-v4-flash-vision-exp",
        base_url="https://api.deepseek.com",
        ffmpeg=executable,
        ffprobe=executable,
        timeout_seconds=30,
        max_stdout_bytes=1024,
        max_stderr_bytes=1024,
        max_workspace_bytes=1024 * 1024,
        max_workspace_files=16,
        max_frames=8,
        max_image_bytes=1024,
        workspace_poll_seconds=0.1,
        terminate_grace_seconds=1,
    )
    supervisor = FakeSupervisor()
    workspace = tmp_path / "job"
    (workspace / "work").mkdir(parents=True)
    video = workspace / "video.bin"
    video.write_bytes(b"video")
    extractor = DeepSeekFrameExtractor(
        config,
        supervisor=supervisor,  # type: ignore[arg-type]
    )

    frames = await extractor.extract(video, workspace=workspace, duration_ms=2_000)

    assert [frame.timestamp_ms for frame in frames] == [0, 500]
    assert supervisor.argv[0] == sys.executable
    assert "-an" in supervisor.argv
    assert "-sn" in supervisor.argv
    assert "-frames:v" in supervisor.argv
    assert all("http" not in value for value in supervisor.argv)
