from __future__ import annotations

from dataclasses import dataclass

from app.domain.analysis.enums import AnalysisValidationCode
from app.domain.analysis.errors import AnalysisValidationError
from app.domain.analysis.text import identifier, non_negative_integer, required_text


def _evidence(values: tuple[str, ...]) -> tuple[str, ...]:
    if not isinstance(values, tuple) or not values:
        raise AnalysisValidationError(
            AnalysisValidationCode.INVALID_EVIDENCE,
            "evidence_segment_ids cannot be empty",
        )
    normalized = tuple(identifier(value, "evidence segment id") for value in values)
    if len(set(normalized)) != len(normalized):
        raise AnalysisValidationError(
            AnalysisValidationCode.DUPLICATE_IDENTIFIER,
            "evidence segment ids cannot be duplicated",
        )
    return normalized


@dataclass(frozen=True, slots=True)
class AnalysisLimits:
    max_mind_map_depth: int = 8
    max_mind_map_nodes: int = 256
    max_collection_items: int = 256
    max_string_characters: int = 8_000
    max_total_characters: int = 200_000

    def __post_init__(self) -> None:
        if any(
            isinstance(value, bool) or value <= 0
            for value in (
                self.max_mind_map_depth,
                self.max_mind_map_nodes,
                self.max_collection_items,
                self.max_string_characters,
                self.max_total_characters,
            )
        ):
            raise ValueError("analysis limits must be positive")


@dataclass(frozen=True, slots=True)
class EvidenceStatement:
    text: str
    evidence_segment_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "text", required_text(self.text, "statement text"))
        object.__setattr__(
            self, "evidence_segment_ids", _evidence(self.evidence_segment_ids)
        )


@dataclass(frozen=True, slots=True)
class AnalysisChapter:
    title: str
    start_ms: int
    end_ms: int
    summary: str
    evidence_segment_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "title", required_text(self.title, "chapter title"))
        start = non_negative_integer(self.start_ms, "chapter start_ms")
        end = non_negative_integer(self.end_ms, "chapter end_ms")
        if end <= start:
            raise AnalysisValidationError(
                AnalysisValidationCode.INVALID_TIME_RANGE,
                "chapter end_ms must be greater than start_ms",
            )
        object.__setattr__(
            self, "summary", required_text(self.summary, "chapter summary")
        )
        object.__setattr__(
            self, "evidence_segment_ids", _evidence(self.evidence_segment_ids)
        )


@dataclass(frozen=True, slots=True)
class MindMapNode:
    id: str
    title: str
    summary: str | None
    start_ms: int | None
    evidence_segment_ids: tuple[str, ...]
    children: tuple[MindMapNode, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", identifier(self.id, "mind map node id"))
        object.__setattr__(self, "title", required_text(self.title, "node title"))
        if self.summary is not None:
            object.__setattr__(
                self, "summary", required_text(self.summary, "node summary")
            )
        if self.start_ms is not None:
            non_negative_integer(self.start_ms, "node start_ms")
        object.__setattr__(
            self, "evidence_segment_ids", _evidence(self.evidence_segment_ids)
        )
        if not isinstance(self.children, tuple):
            raise AnalysisValidationError(
                AnalysisValidationCode.INVALID_SCHEMA,
                "mind map children must be a tuple",
            )


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    schema_version: str
    language: str
    title: str
    summary: EvidenceStatement
    key_points: tuple[EvidenceStatement, ...]
    action_items: tuple[EvidenceStatement, ...]
    chapters: tuple[AnalysisChapter, ...]
    mind_map: MindMapNode

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "schema_version",
            required_text(self.schema_version, "schema version", maximum=128),
        )
        object.__setattr__(
            self, "language", required_text(self.language, "language", maximum=35)
        )
        object.__setattr__(self, "title", required_text(self.title, "title"))
        if not self.key_points or not self.chapters:
            raise AnalysisValidationError(
                AnalysisValidationCode.INVALID_SCHEMA,
                "key_points and chapters cannot be empty",
            )
