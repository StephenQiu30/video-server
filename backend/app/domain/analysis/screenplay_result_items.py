from __future__ import annotations

from dataclasses import dataclass

from app.domain.analysis.enums import AnalysisValidationCode
from app.domain.analysis.errors import AnalysisValidationError
from app.domain.analysis.result_items import _references, _strings
from app.domain.analysis.text import identifier, required_text


@dataclass(frozen=True, slots=True)
class ScreenplayEvidenceItem:
    id: str
    title: str
    description: str
    evidence_scene_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", identifier(self.id, "evidence item id"))
        object.__setattr__(self, "title", required_text(self.title, "item title"))
        object.__setattr__(
            self, "description", required_text(self.description, "item description")
        )
        object.__setattr__(
            self,
            "evidence_scene_ids",
            _references(self.evidence_scene_ids, "evidence source scene id"),
        )


@dataclass(frozen=True, slots=True)
class ScreenplayStructure:
    acts: tuple[ScreenplayEvidenceItem, ...]
    turning_points: tuple[ScreenplayEvidenceItem, ...]
    pacing_summary: str

    def __post_init__(self) -> None:
        if not self.acts:
            raise AnalysisValidationError(
                AnalysisValidationCode.INVALID_SCHEMA,
                "screenplay structure must contain at least one act",
            )
        object.__setattr__(
            self,
            "pacing_summary",
            required_text(self.pacing_summary, "structure pacing summary"),
        )


@dataclass(frozen=True, slots=True)
class ScreenplayCharacter:
    id: str
    name: str
    goal: str
    conflict: str
    arc: str
    evidence_scene_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", identifier(self.id, "character id"))
        for field_name in ("name", "goal", "conflict", "arc"):
            object.__setattr__(
                self,
                field_name,
                required_text(getattr(self, field_name), f"character {field_name}"),
            )
        object.__setattr__(
            self,
            "evidence_scene_ids",
            _references(self.evidence_scene_ids, "character evidence source scene id"),
        )


@dataclass(frozen=True, slots=True)
class ScreenplayScene:
    id: str
    source_scene_id: str
    purpose: str
    conflict: str
    turn: str
    pacing: str
    findings: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", identifier(self.id, "scene result id"))
        object.__setattr__(
            self,
            "source_scene_id",
            identifier(self.source_scene_id, "source scene id"),
        )
        for field_name in ("purpose", "conflict", "turn", "pacing"):
            object.__setattr__(
                self,
                field_name,
                required_text(getattr(self, field_name), f"scene {field_name}"),
            )
        object.__setattr__(self, "findings", _strings(self.findings, "scene finding"))
