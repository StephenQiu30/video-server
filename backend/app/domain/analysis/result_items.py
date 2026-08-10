from __future__ import annotations

from dataclasses import dataclass

from app.domain.analysis.enums import AnalysisValidationCode
from app.domain.analysis.errors import AnalysisValidationError
from app.domain.analysis.text import identifier, non_negative_integer, required_text


def _references(values: tuple[str, ...], field: str) -> tuple[str, ...]:
    if not isinstance(values, tuple) or not values:
        raise AnalysisValidationError(
            AnalysisValidationCode.INVALID_EVIDENCE,
            f"{field} cannot be empty",
        )
    normalized = tuple(identifier(value, field) for value in values)
    if len(set(normalized)) != len(normalized):
        raise AnalysisValidationError(
            AnalysisValidationCode.DUPLICATE_IDENTIFIER,
            f"{field} cannot contain duplicates",
        )
    return normalized


def _strings(values: tuple[str, ...], field: str) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise AnalysisValidationError(
            AnalysisValidationCode.INVALID_SCHEMA,
            f"{field} must be a tuple",
        )
    normalized = tuple(required_text(value, field, maximum=128) for value in values)
    if len(set(normalized)) != len(normalized):
        raise AnalysisValidationError(
            AnalysisValidationCode.DUPLICATE_IDENTIFIER,
            f"{field} cannot contain duplicates",
        )
    return normalized


@dataclass(frozen=True, slots=True)
class Shot:
    id: str
    index: int
    start_ms: int
    end_ms: int
    representative_frame_ms: int
    description: str
    transition_in: str
    shot_size: str
    camera_motion: str
    narrative_function: str
    highlight_score: int
    visual_tags: tuple[str, ...]
    asset_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", identifier(self.id, "shot id"))
        if isinstance(self.index, bool) or not isinstance(self.index, int):
            raise AnalysisValidationError(
                AnalysisValidationCode.INVALID_SCHEMA,
                "shot index must be an integer",
            )
        start = non_negative_integer(self.start_ms, "shot start_ms")
        end = non_negative_integer(self.end_ms, "shot end_ms")
        representative = non_negative_integer(
            self.representative_frame_ms,
            "shot representative_frame_ms",
        )
        if end <= start or not start <= representative < end:
            raise AnalysisValidationError(
                AnalysisValidationCode.INVALID_TIME_RANGE,
                "shot time range or representative frame is invalid",
            )
        object.__setattr__(
            self, "description", required_text(self.description, "shot description")
        )
        for field in ("transition_in", "shot_size", "camera_motion"):
            object.__setattr__(
                self,
                field,
                required_text(getattr(self, field), field, maximum=32),
            )
        object.__setattr__(
            self,
            "narrative_function",
            required_text(self.narrative_function, "shot narrative function"),
        )
        if (
            isinstance(self.highlight_score, bool)
            or not isinstance(self.highlight_score, int)
            or not 1 <= self.highlight_score <= 5
        ):
            raise AnalysisValidationError(
                AnalysisValidationCode.INVALID_SCHEMA,
                "shot highlight_score must be between 1 and 5",
            )
        object.__setattr__(
            self, "visual_tags", _strings(self.visual_tags, "visual tag")
        )
        object.__setattr__(self, "asset_ids", _strings(self.asset_ids, "asset id"))


@dataclass(frozen=True, slots=True)
class Highlight:
    id: str
    title: str
    description: str
    score: int
    reason: str
    start_ms: int
    end_ms: int
    evidence_shot_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", identifier(self.id, "highlight id"))
        object.__setattr__(self, "title", required_text(self.title, "highlight title"))
        object.__setattr__(
            self,
            "description",
            required_text(self.description, "highlight description"),
        )
        if isinstance(self.score, bool) or not isinstance(self.score, int):
            raise AnalysisValidationError(
                AnalysisValidationCode.INVALID_SCHEMA,
                "highlight score must be an integer",
            )
        if not 0 <= self.score <= 100:
            raise AnalysisValidationError(
                AnalysisValidationCode.INVALID_SCHEMA,
                "highlight score must be between 0 and 100",
            )
        object.__setattr__(
            self, "reason", required_text(self.reason, "highlight reason")
        )
        start = non_negative_integer(self.start_ms, "highlight start_ms")
        end = non_negative_integer(self.end_ms, "highlight end_ms")
        if end <= start:
            raise AnalysisValidationError(
                AnalysisValidationCode.INVALID_TIME_RANGE,
                "highlight time range is invalid",
            )
        object.__setattr__(
            self,
            "evidence_shot_ids",
            _references(self.evidence_shot_ids, "highlight evidence shot id"),
        )


@dataclass(frozen=True, slots=True)
class VisualAsset:
    id: str
    type: str
    label: str
    description: str
    first_seen_ms: int
    evidence_shot_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", identifier(self.id, "asset id"))
        object.__setattr__(
            self, "type", required_text(self.type, "asset type", maximum=32)
        )
        object.__setattr__(self, "label", required_text(self.label, "asset label"))
        object.__setattr__(
            self,
            "description",
            required_text(self.description, "asset description"),
        )
        non_negative_integer(self.first_seen_ms, "asset first_seen_ms")
        object.__setattr__(
            self,
            "evidence_shot_ids",
            _references(self.evidence_shot_ids, "asset evidence shot id"),
        )
