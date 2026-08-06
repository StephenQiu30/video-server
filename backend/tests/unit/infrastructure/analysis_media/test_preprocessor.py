from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from app.infrastructure.analysis_media import (
    AnalysisMediaSettings,
    FfmpegAudioPreprocessor,
    MediaPreprocessingError,
)
from app.runner.process import ProcessResult, ProcessTimeoutError
from tests.unit.infrastructure.analysis_media.helpers import (
    ScriptedProcessRunner,
    probe,
    write_output,
)


def source_file(workspace: Path) -> Path:
    source = workspace / "artifact.mp4"
    source.write_bytes(b"local-media")
    return source


@pytest.mark.asyncio
async def test_extracts_fixed_audio_and_returns_absolute_offsets(
    tmp_path: Path,
) -> None:
    source = source_file(tmp_path)
    runner = ScriptedProcessRunner(
        probe(2.25),
        write_output(b"RIFF-one"),
        write_output(b"RIFF-two"),
        write_output(b"RIFF-last"),
    )
    settings = AnalysisMediaSettings(chunk_duration_ms=1_000)

    chunks = await FfmpegAudioPreprocessor(settings, runner).extract_chunks(
        source, workspace=tmp_path
    )

    assert [(item.index, item.start_ms, item.end_ms) for item in chunks] == [
        (0, 0, 1_000),
        (1, 1_000, 2_000),
        (2, 2_000, 2_250),
    ]
    assert [item.content for item in chunks] == [b"RIFF-one", b"RIFF-two", b"RIFF-last"]
    first_extract = runner.calls[1][0]
    assert first_extract[:5] == (
        "ffmpeg",
        "-nostdin",
        "-hide_banner",
        "-loglevel",
        "error",
    )
    assert _option(first_extract, "-ss") == "0.000"
    assert _option(first_extract, "-t") == "1.000"
    assert _option(first_extract, "-ac") == "1"
    assert _option(first_extract, "-ar") == "16000"
    assert _option(first_extract, "-c:a") == "pcm_s16le"
    assert _option(runner.calls[3][0], "-ss") == "2.000"
    assert _option(runner.calls[3][0], "-t") == "0.250"
    probe_command, cwd, timeout, env = runner.calls[0]
    assert probe_command == (
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "a:0",
        "-show_entries",
        "format=duration:stream=codec_type",
        "-of",
        "json",
        "-protocol_whitelist",
        "file,crypto,data",
        str(source),
    )
    assert cwd.is_relative_to(tmp_path)
    assert timeout == 30.0
    assert env is not None and env["HOME"] == str(cwd)
    assert "HTTP_PROXY" not in env
    assert list(tmp_path.iterdir()) == [source]


@pytest.mark.asyncio
async def test_failure_timeout_and_cancel_clean_temporary_files(tmp_path: Path) -> None:
    source = source_file(tmp_path)
    timeout = ProcessTimeoutError(ProcessResult(-15, b"", b"", False, False))
    cases: tuple[tuple[BaseException | ProcessResult, str | None], ...] = (
        (ProcessResult(1, b"", b"failure", False, False), "audio_extraction_failed"),
        (timeout, "audio_extraction_timeout"),
        (asyncio.CancelledError(), None),
    )
    for failure, expected_code in cases:
        runner = ScriptedProcessRunner(probe(1), failure)
        processor = FfmpegAudioPreprocessor(AnalysisMediaSettings(), runner)
        if expected_code is None:
            with pytest.raises(asyncio.CancelledError):
                await processor.extract_chunks(source, workspace=tmp_path)
        else:
            with pytest.raises(MediaPreprocessingError) as captured:
                await processor.extract_chunks(source, workspace=tmp_path)
            assert captured.value.code == expected_code
        assert list(tmp_path.iterdir()) == [source]


def _option(command: tuple[str, ...], name: str) -> str:
    return command[command.index(name) + 1]
