from __future__ import annotations

from dataclasses import dataclass

from app.domain.analysis.enums import AnalysisValidationCode
from app.domain.analysis.errors import AnalysisValidationError
from app.domain.analysis.result_items import Highlight, Shot, VisualAsset, _references
from app.domain.analysis.text import non_negative_integer, required_text


@dataclass(frozen=True, slots=True)
class AnalysisLimits:
    max_collection_items: int = 512
    max_string_characters: int = 8_000
    max_total_characters: int = 200_000

    def __post_init__(self) -> None:
        values = (
            self.max_collection_items,
            self.max_string_characters,
            self.max_total_characters,
        )
        if any(isinstance(value, bool) or value <= 0 for value in values):
            raise ValueError("analysis limits must be positive")


@dataclass(frozen=True, slots=True)
class AnalysisMedia:
    duration_ms: int
    container: str
    size_bytes: int

    def __post_init__(self) -> None:
        duration = non_negative_integer(self.duration_ms, "media duration_ms")
        size = non_negative_integer(self.size_bytes, "media size_bytes")
        if duration == 0 or size == 0:
            raise AnalysisValidationError(
                AnalysisValidationCode.INVALID_TIME_RANGE,
                "media duration and size must be positive",
            )
        object.__setattr__(
            self,
            "container",
            required_text(self.container, "media container", maximum=16),
        )


@dataclass(frozen=True, slots=True)
class EvidenceSummary:
    text: str
    evidence_shot_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "text", required_text(self.text, "summary text"))
        object.__setattr__(
            self,
            "evidence_shot_ids",
            _references(self.evidence_shot_ids, "summary evidence shot id"),
        )


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    schema_version: str
    language: str
    title: str
    summary: EvidenceSummary
    media: AnalysisMedia
    shot_count: int
    shots: tuple[Shot, ...]
    highlights: tuple[Highlight, ...]
    assets: tuple[VisualAsset, ...]

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
        if not self.shots or self.shot_count != len(self.shots):
            raise AnalysisValidationError(
                AnalysisValidationCode.INVALID_SCHEMA,
                "shot_count must equal a non-empty shots collection",
            )
