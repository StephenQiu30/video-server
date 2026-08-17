from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from .errors import AnalysisArtifactError
from .models import ScreenplaySceneSource


@dataclass(frozen=True, slots=True)
class ScreenplayRewriteSourceChunk:
    source_scene_id: str
    part_no: int
    start: int
    end: int
    source_sha256: str
    text: str = field(repr=False)

    def __post_init__(self) -> None:
        if (
            not self.source_scene_id
            or isinstance(self.part_no, bool)
            or not isinstance(self.part_no, int)
            or self.part_no <= 0
            or any(
                isinstance(value, bool) or not isinstance(value, int)
                for value in (self.start, self.end)
            )
            or not 0 <= self.start < self.end
            or len(self.source_sha256) != 64
            or any(value not in "0123456789abcdef" for value in self.source_sha256)
            or not self.text
            or len(self.text) != self.end - self.start
        ):
            raise ValueError("invalid screenplay rewrite source chunk")


def plan_screenplay_rewrite(
    text: str,
    scenes: tuple[ScreenplaySceneSource, ...],
    *,
    max_chunk_characters: int,
    max_chunks: int,
) -> tuple[ScreenplayRewriteSourceChunk, ...]:
    limits = (max_chunk_characters, max_chunks)
    if any(
        isinstance(value, bool) or not isinstance(value, int) or value <= 0
        for value in limits
    ):
        raise ValueError("rewrite planning limits must be positive")
    _validate_source(text, scenes)
    chunks: list[ScreenplayRewriteSourceChunk] = []
    owned_start = 0
    for scene in scenes:
        part_no = 1
        cursor = owned_start
        while cursor < scene.end:
            boundary = _chunk_boundary(text, cursor, scene.end, max_chunk_characters)
            source_text = text[cursor:boundary]
            chunks.append(
                ScreenplayRewriteSourceChunk(
                    source_scene_id=scene.id,
                    part_no=part_no,
                    start=cursor,
                    end=boundary,
                    source_sha256=hashlib.sha256(source_text.encode()).hexdigest(),
                    text=source_text,
                )
            )
            if len(chunks) > max_chunks:
                raise AnalysisArtifactError("analysis_resource_limit")
            cursor = boundary
            part_no += 1
        owned_start = scene.end
    if "".join(chunk.text for chunk in chunks) != text:
        raise AnalysisArtifactError("artifact_integrity_failed")
    return tuple(chunks)


def plan_screenplay_glossary_chunks(
    text: str, *, max_chunk_characters: int
) -> tuple[str, ...]:
    """Split glossary input into bounded, boundary-aware segments.

    Glossary extraction is a separate model call from chunk rewriting.  Keeping
    these segments independent from the rewrite plan lets a large screenplay
    use a small number of glossary calls without changing the source-bound
    rewrite coverage.
    """
    if (
        isinstance(max_chunk_characters, bool)
        or not isinstance(max_chunk_characters, int)
        or max_chunk_characters <= 0
    ):
        raise ValueError("glossary planning limit must be positive")
    if not text or "\r" in text or "\x00" in text:
        raise AnalysisArtifactError("artifact_integrity_failed")
    chunks: list[str] = []
    cursor = 0
    while cursor < len(text):
        boundary = _chunk_boundary(text, cursor, len(text), max_chunk_characters)
        chunks.append(text[cursor:boundary])
        cursor = boundary
    if "".join(chunks) != text:
        raise AnalysisArtifactError("artifact_integrity_failed")
    return tuple(chunks)


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


def _chunk_boundary(text: str, start: int, end: int, maximum: int) -> int:
    upper = min(start + maximum, end)
    if upper == end:
        return end
    threshold = start + max(1, maximum // 2)
    paragraph = text.rfind("\n\n", threshold, upper)
    if paragraph >= threshold:
        return paragraph + 2
    line = text.rfind("\n", threshold, upper)
    if line >= threshold:
        return line + 1
    space = text.rfind(" ", threshold, upper)
    if space >= threshold:
        return space + 1
    return upper
