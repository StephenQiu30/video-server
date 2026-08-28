from __future__ import annotations

from dataclasses import dataclass

from app.domain.analysis.enums import AnalysisValidationCode
from app.domain.analysis.errors import AnalysisValidationError
from app.domain.analysis.result_items import _references, _strings
from app.domain.analysis.text import identifier, non_negative_integer, required_text


@dataclass(frozen=True, slots=True)
class VideoScene:
    id: str
    index: int
    title: str
    start_ms: int
    end_ms: int
    location: str
    description: str
    narrative_function: str
    visual_rules: tuple[str, ...]
    continuity_risks: tuple[str, ...]
    evidence_shot_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", identifier(self.id, "scene id"))
        if (
            isinstance(self.index, bool)
            or not isinstance(self.index, int)
            or self.index <= 0
        ):
            raise AnalysisValidationError(
                AnalysisValidationCode.INVALID_SCHEMA,
                "scene index must be a positive integer",
            )
        start = non_negative_integer(self.start_ms, "scene start_ms")
        end = non_negative_integer(self.end_ms, "scene end_ms")
        if end <= start:
            raise AnalysisValidationError(
                AnalysisValidationCode.INVALID_TIME_RANGE,
                "scene time range is invalid",
            )
        for field in ("title", "location", "description", "narrative_function"):
            object.__setattr__(
                self,
                field,
                required_text(getattr(self, field), f"scene {field}"),
            )
        visual_rules = _strings(self.visual_rules, "scene visual rule")
        if not visual_rules:
            raise AnalysisValidationError(
                AnalysisValidationCode.INVALID_SCHEMA,
                "scene visual rules cannot be empty",
            )
        object.__setattr__(self, "visual_rules", visual_rules)
        object.__setattr__(
            self,
            "continuity_risks",
            _strings(self.continuity_risks, "scene continuity risk"),
        )
        object.__setattr__(
            self,
            "evidence_shot_ids",
            _references(self.evidence_shot_ids, "scene evidence shot id"),
        )
