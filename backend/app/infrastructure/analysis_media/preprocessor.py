from __future__ import annotations

from pathlib import Path

from app.application.analysis import AudioChunk
from app.runner.process import ProcessSupervisor

from .commands import AnalysisMediaCommands, ProcessRunner
from .errors import MediaPreprocessingError
from .paths import (
    cleanup_processing_directory,
    create_processing_directory,
    media_artifact,
    read_chunk,
    workspace_root,
)
from .settings import AnalysisMediaSettings


class FfmpegAudioPreprocessor:
    def __init__(
        self,
        settings: AnalysisMediaSettings,
        process_runner: ProcessRunner | None = None,
    ) -> None:
        runner = process_runner or ProcessSupervisor(
            output_limit_bytes=settings.output_capture_bytes,
            terminate_grace_seconds=settings.terminate_grace_seconds,
        )
        self._settings = settings
        self._commands = AnalysisMediaCommands(settings, runner)

    async def extract_chunks(
        self, artifact: Path, *, workspace: Path
    ) -> tuple[AudioChunk, ...]:
        root = workspace_root(workspace)
        source = media_artifact(artifact, root)
        processing = create_processing_directory(root)
        try:
            duration_ms = await self._commands.probe_duration_ms(source, processing)
            boundaries = self._boundaries(duration_ms)
            chunks: list[AudioChunk] = []
            total_bytes = 0
            for index, (start_ms, end_ms) in enumerate(boundaries):
                output = processing / f"chunk-{index:06d}.wav"
                await self._commands.extract(
                    source,
                    output,
                    start_ms=start_ms,
                    end_ms=end_ms,
                    cwd=processing,
                )
                content = read_chunk(
                    output,
                    root=root,
                    processing=processing,
                    max_bytes=self._settings.max_chunk_bytes,
                )
                total_bytes += len(content)
                if total_bytes > self._settings.max_total_bytes:
                    raise MediaPreprocessingError("total_audio_bytes_exceeded")
                chunks.append(AudioChunk(index, start_ms, end_ms, content))
            return tuple(chunks)
        finally:
            cleanup_processing_directory(processing)

    def _boundaries(self, duration_ms: int) -> tuple[tuple[int, int], ...]:
        if duration_ms > self._settings.max_total_duration_ms:
            raise MediaPreprocessingError("duration_limit_exceeded")
        chunk_duration = self._settings.chunk_duration_ms
        count = (duration_ms + chunk_duration - 1) // chunk_duration
        if count > self._settings.max_chunks:
            raise MediaPreprocessingError("chunk_count_exceeded")
        return tuple(
            (start, min(start + chunk_duration, duration_ms))
            for start in range(0, duration_ms, chunk_duration)
        )
