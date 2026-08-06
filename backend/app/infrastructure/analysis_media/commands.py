from __future__ import annotations

import json
import math
import os
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Protocol

from app.runner.process import ProcessResult, ProcessTimeoutError

from .errors import MediaPreprocessingError
from .settings import AnalysisMediaSettings


class ProcessRunner(Protocol):
    async def run(
        self,
        argv: Sequence[str],
        *,
        cwd: Path,
        timeout_seconds: float,
        env: Mapping[str, str] | None = None,
    ) -> ProcessResult: ...


class AnalysisMediaCommands:
    def __init__(self, settings: AnalysisMediaSettings, runner: ProcessRunner) -> None:
        self._settings = settings
        self._runner = runner

    async def probe_duration_ms(self, source: Path, cwd: Path) -> int:
        command = (
            self._settings.ffprobe_bin,
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
        result = await self._run(
            command,
            cwd,
            self._settings.probe_timeout_seconds,
            timeout_code="media_probe_timeout",
            failure_code="media_probe_failed",
        )
        return _duration_ms(result.stdout)

    async def extract(
        self,
        source: Path,
        output: Path,
        *,
        start_ms: int,
        end_ms: int,
        cwd: Path,
    ) -> None:
        command = (
            self._settings.ffmpeg_bin,
            "-nostdin",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-ss",
            _seconds(start_ms),
            "-t",
            _seconds(end_ms - start_ms),
            "-protocol_whitelist",
            "file,crypto,data",
            "-i",
            str(source),
            "-map",
            "0:a:0",
            "-vn",
            "-sn",
            "-dn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-c:a",
            "pcm_s16le",
            "-map_metadata",
            "-1",
            "-fflags",
            "+bitexact",
            "-flags:a",
            "+bitexact",
            "-f",
            "wav",
            str(output),
        )
        await self._run(
            command,
            cwd,
            self._settings.extraction_timeout_seconds,
            timeout_code="audio_extraction_timeout",
            failure_code="audio_extraction_failed",
        )

    async def _run(
        self,
        command: Sequence[str],
        cwd: Path,
        timeout: float,
        *,
        timeout_code: str,
        failure_code: str,
    ) -> ProcessResult:
        try:
            result = await self._runner.run(
                command,
                cwd=cwd,
                timeout_seconds=timeout,
                env=_child_environment(cwd),
            )
        except ProcessTimeoutError as exc:
            raise MediaPreprocessingError(timeout_code) from exc
        except OSError as exc:
            raise MediaPreprocessingError("media_dependency_unavailable") from exc
        if result.returncode != 0:
            raise MediaPreprocessingError(failure_code)
        return result


def _duration_ms(raw: bytes) -> int:
    try:
        payload = json.loads(raw)
        streams = payload["streams"]
        duration = float(payload["format"]["duration"])
        has_audio = any(item.get("codec_type") == "audio" for item in streams)
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise MediaPreprocessingError("invalid_media_metadata") from exc
    if not has_audio or not math.isfinite(duration) or duration <= 0:
        raise MediaPreprocessingError("invalid_media_metadata")
    return math.ceil(duration * 1000)


def _seconds(milliseconds: int) -> str:
    return f"{milliseconds / 1000:.3f}"


def _child_environment(cwd: Path) -> dict[str, str]:
    return {
        "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
        "HOME": str(cwd),
        "TMPDIR": str(cwd),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
    }
