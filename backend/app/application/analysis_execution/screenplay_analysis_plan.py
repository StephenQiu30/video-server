from __future__ import annotations

from dataclasses import dataclass, field

from .errors import AnalysisArtifactError
from .models import ScreenplaySceneSource


@dataclass(frozen=True, slots=True)
class ScreenplayAnalysisSourceChunk:
    start: int
    end: int
    scenes: tuple[ScreenplaySceneSource, ...]
    text: str = field(repr=False)

    def __post_init__(self) -> None:
        if (
            not 0 <= self.start < self.end
            or not self.scenes
            or not self.text
            or len(self.text) != self.end - self.start
        ):
            raise ValueError("invalid screenplay analysis source chunk")


def plan_screenplay_analysis(
    text: str,
    scenes: tuple[ScreenplaySceneSource, ...],
    *,
    max_chunk_characters: int,
    max_chunk_scenes: int,
    max_chunks: int,
) -> tuple[ScreenplayAnalysisSourceChunk, ...]:
    limits = (max_chunk_characters, max_chunk_scenes, max_chunks)
    if any(
        isinstance(value, bool) or not isinstance(value, int) or value <= 0
        for value in limits
    ):
        raise ValueError("screenplay analysis planning limits must be positive")
    _validate_source(text, scenes)
    chunks: list[ScreenplayAnalysisSourceChunk] = []
    chunk_start = 0
    chunk_scenes: list[ScreenplaySceneSource] = []
    previous_end = 0
    for scene in scenes:
        owned_size = scene.end - previous_end
        if owned_size > max_chunk_characters:
            raise AnalysisArtifactError("analysis_resource_limit")
        exceeds = chunk_scenes and (
            scene.end - chunk_start > max_chunk_characters
            or len(chunk_scenes) >= max_chunk_scenes
        )
        if exceeds:
            chunks.append(_chunk(text, chunk_start, previous_end, tuple(chunk_scenes)))
            if len(chunks) >= max_chunks:
                raise AnalysisArtifactError("analysis_resource_limit")
            chunk_start = previous_end
            chunk_scenes = []
        chunk_scenes.append(scene)
        previous_end = scene.end
    chunks.append(_chunk(text, chunk_start, previous_end, tuple(chunk_scenes)))
    if len(chunks) > max_chunks:
        raise AnalysisArtifactError("analysis_resource_limit")
    return tuple(chunks)


def _chunk(
    text: str,
    start: int,
    end: int,
    scenes: tuple[ScreenplaySceneSource, ...],
) -> ScreenplayAnalysisSourceChunk:
    return ScreenplayAnalysisSourceChunk(start, end, scenes, text[start:end])


def _validate_source(text: str, scenes: tuple[ScreenplaySceneSource, ...]) -> None:
    if (
        not text
        or "\r" in text
        or "\x00" in text
        or not text.endswith("\n")
        or not scenes
        or len({scene.id for scene in scenes}) != len(scenes)
        or scenes[-1].end != len(text)
    ):
        raise AnalysisArtifactError("artifact_integrity_failed")
    for index, scene in enumerate(scenes):
        if index > 0 and scenes[index - 1].end != scene.start:
            raise AnalysisArtifactError("artifact_integrity_failed")
