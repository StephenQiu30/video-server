from __future__ import annotations

from pathlib import Path

import pytest
from app.infrastructure.analysis_media import (
    AnalysisMediaSettings,
    FfmpegAudioPreprocessor,
    MediaPreprocessingError,
)
from tests.unit.infrastructure.analysis_media.helpers import (
    ScriptedProcessRunner,
    probe,
    success,
    write_output,
)


def source_file(workspace: Path, content: bytes = b"media") -> Path:
    source = workspace / "artifact.mp4"
    source.write_bytes(content)
    return source


@pytest.mark.asyncio
async def test_rejects_duration_and_chunk_count_before_extracting(
    tmp_path: Path,
) -> None:
    cases = (
        (
            2.001,
            AnalysisMediaSettings(max_total_duration_ms=2_000),
            "duration_limit_exceeded",
        ),
        (
            3,
            AnalysisMediaSettings(chunk_duration_ms=1_000, max_chunks=2),
            "chunk_count_exceeded",
        ),
    )
    for index, (duration, settings, code) in enumerate(cases):
        workspace = tmp_path / str(index)
        workspace.mkdir()
        source = source_file(workspace)
        runner = ScriptedProcessRunner(probe(duration))
        with pytest.raises(MediaPreprocessingError) as captured:
            await FfmpegAudioPreprocessor(settings, runner).extract_chunks(
                source, workspace=workspace
            )
        assert captured.value.code == code
        assert len(runner.calls) == 1


@pytest.mark.asyncio
async def test_rejects_output_byte_limits_and_empty_files(
    tmp_path: Path,
) -> None:
    cases = (
        ((b"12345",), AnalysisMediaSettings(max_chunk_bytes=4), "chunk_size_exceeded"),
        (
            (b"123456", b"123456"),
            AnalysisMediaSettings(chunk_duration_ms=1_000, max_total_bytes=10),
            "total_audio_bytes_exceeded",
        ),
        ((b"",), AnalysisMediaSettings(), "invalid_chunk_output"),
    )
    for index, (payloads, settings, code) in enumerate(cases):
        workspace = tmp_path / str(index)
        workspace.mkdir()
        source = source_file(workspace)
        duration = 2 if len(payloads) == 2 else 1
        runner = ScriptedProcessRunner(
            probe(duration), *(write_output(item) for item in payloads)
        )
        with pytest.raises(MediaPreprocessingError) as captured:
            await FfmpegAudioPreprocessor(settings, runner).extract_chunks(
                source, workspace=workspace
            )
        assert captured.value.code == code
        assert list(workspace.iterdir()) == [source]


@pytest.mark.asyncio
async def test_rejects_symlink_chunk_output(tmp_path: Path) -> None:
    source = source_file(tmp_path)
    target = tmp_path / "outside.wav"
    target.write_bytes(b"RIFF")

    def symlink_output(command: tuple[str, ...], _cwd: Path):  # type: ignore[no-untyped-def]
        Path(command[-1]).symlink_to(target)
        return success()

    runner = ScriptedProcessRunner(probe(1), symlink_output)

    with pytest.raises(MediaPreprocessingError) as captured:
        await FfmpegAudioPreprocessor(AnalysisMediaSettings(), runner).extract_chunks(
            source, workspace=tmp_path
        )

    assert captured.value.code == "invalid_chunk_output"
    assert not any(
        path.name.startswith(".analysis-audio-") for path in tmp_path.iterdir()
    )


@pytest.mark.asyncio
async def test_rejects_unsafe_input_artifacts(tmp_path: Path) -> None:
    cases = ("outside", "symlink", "empty")
    for kind in cases:
        workspace = tmp_path / kind
        workspace.mkdir()
        outside = tmp_path / f"{kind}.mp4"
        outside.write_bytes(b"media")
        source = outside
        if kind == "symlink":
            source = workspace / "artifact.mp4"
            source.symlink_to(outside)
        elif kind == "empty":
            source = workspace / "artifact.mp4"
            source.write_bytes(b"")
        runner = ScriptedProcessRunner()
        with pytest.raises(MediaPreprocessingError) as captured:
            await FfmpegAudioPreprocessor(
                AnalysisMediaSettings(), runner
            ).extract_chunks(source, workspace=workspace)
        assert captured.value.code == "invalid_media_artifact"
        assert runner.calls == []


def test_defaults_leave_room_below_provider_limit() -> None:
    settings = AnalysisMediaSettings()
    assert settings.max_chunk_bytes == 24_000_000
    assert settings.max_chunk_bytes < 25_000_000
