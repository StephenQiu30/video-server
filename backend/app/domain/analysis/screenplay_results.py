from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from app.domain.analysis.enums import AnalysisResultKind, AnalysisValidationCode
from app.domain.analysis.errors import AnalysisValidationError
from app.domain.analysis.result_items import _strings
from app.domain.analysis.screenplay_result_items import (
    ScreenplayCharacter,
    ScreenplayEvidenceItem,
    ScreenplayScene,
    ScreenplayStructure,
)
from app.domain.analysis.screenplay_rewrite_items import (
    ScreenplayGlossaryTerm,
    ScreenplayRewriteChunk,
)
from app.domain.analysis.text import required_text


@dataclass(frozen=True, slots=True)
class ScreenplayAnalysisResult:
    language: str
    title: str
    logline: str
    synopsis: str
    structure: ScreenplayStructure
    characters: tuple[ScreenplayCharacter, ...]
    scenes: tuple[ScreenplayScene, ...]
    dialogue_findings: tuple[ScreenplayEvidenceItem, ...]
    strengths: tuple[ScreenplayEvidenceItem, ...]
    priority_revisions: tuple[ScreenplayEvidenceItem, ...]
    kind: AnalysisResultKind = field(
        init=False, default=AnalysisResultKind.SCREENPLAY_ANALYSIS
    )

    def __post_init__(self) -> None:
        for field_name in ("language", "title", "logline", "synopsis"):
            maximum = 35 if field_name == "language" else 8_000
            object.__setattr__(
                self,
                field_name,
                required_text(getattr(self, field_name), field_name, maximum=maximum),
            )
        validate_screenplay_analysis_result(self)


@dataclass(frozen=True, slots=True)
class ScreenplayRewriteResult:
    source_language: str
    target_language: str
    source_scene_count: int
    output_scene_count: int
    glossary: tuple[ScreenplayGlossaryTerm, ...]
    chunks: tuple[ScreenplayRewriteChunk, ...]
    change_summary: tuple[str, ...]
    kind: AnalysisResultKind = field(
        init=False, default=AnalysisResultKind.SCREENPLAY_REWRITE
    )

    def __post_init__(self) -> None:
        for field_name in ("source_language", "target_language"):
            object.__setattr__(
                self,
                field_name,
                required_text(getattr(self, field_name), field_name, maximum=35),
            )
        object.__setattr__(
            self,
            "change_summary",
            _strings(self.change_summary, "rewrite change summary"),
        )
        validate_screenplay_rewrite_result(self)


def validate_screenplay_analysis_result(result: ScreenplayAnalysisResult) -> None:
    if not result.scenes:
        _invalid("screenplay analysis must contain scenes")
    collections = (
        result.characters,
        result.scenes,
        result.structure.acts,
        result.structure.turning_points,
        result.dialogue_findings,
        result.strengths,
        result.priority_revisions,
    )
    if any(len(items) > 512 for items in collections):
        raise AnalysisValidationError(
            AnalysisValidationCode.LIMIT_EXCEEDED,
            "screenplay analysis collection exceeds the item limit",
        )
    _unique_ids(result.scenes, "scene result")
    source_ids = tuple(scene.source_scene_id for scene in result.scenes)
    if len(set(source_ids)) != len(source_ids):
        _duplicate("source scene ids must be unique")
    for values, label in (
        (result.characters, "character"),
        (result.structure.acts, "act"),
        (result.structure.turning_points, "turning point"),
        (result.dialogue_findings, "dialogue finding"),
        (result.strengths, "strength"),
        (result.priority_revisions, "priority revision"),
    ):
        _unique_ids(values, label)
        for item in values:
            if any(
                reference not in source_ids for reference in item.evidence_scene_ids
            ):
                raise AnalysisValidationError(
                    AnalysisValidationCode.INVALID_EVIDENCE,
                    f"{label} references an unknown source scene",
                )


def validate_screenplay_rewrite_result(result: ScreenplayRewriteResult) -> None:
    counts = (result.source_scene_count, result.output_scene_count)
    if any(
        isinstance(value, bool) or not isinstance(value, int) or value <= 0
        for value in counts
    ):
        _invalid("rewrite scene counts must be positive integers")
    if not result.chunks or not result.change_summary:
        _invalid("rewrite chunks and change summary cannot be empty")
    scene_ids = tuple(dict.fromkeys(chunk.source_scene_id for chunk in result.chunks))
    if result.source_scene_count != len(scene_ids):
        _invalid("source_scene_count must equal the rewritten source scenes")
    if result.output_scene_count != result.source_scene_count:
        _invalid("output_scene_count must equal source_scene_count")
    pairs = {(chunk.source_scene_id, chunk.part_no) for chunk in result.chunks}
    if len(pairs) != len(result.chunks):
        _duplicate("rewrite chunks must have unique source scene and part numbers")
    expected_order: list[tuple[str, int]] = []
    for scene_id in scene_ids:
        parts = [
            item.part_no for item in result.chunks if item.source_scene_id == scene_id
        ]
        if parts != list(range(1, len(parts) + 1)):
            _invalid("rewrite chunk parts must be contiguous and ordered")
        expected_order.extend((scene_id, part_no) for part_no in parts)
    actual_order = [(item.source_scene_id, item.part_no) for item in result.chunks]
    if actual_order != expected_order:
        _invalid("rewrite chunks must stay grouped in source scene order")


class _Identified(Protocol):
    @property
    def id(self) -> str: ...


def _unique_ids(values: tuple[_Identified, ...], label: str) -> None:
    identifiers = [value.id for value in values]
    if len(set(identifiers)) != len(identifiers):
        _duplicate(f"{label} ids must be unique")


def _invalid(detail: str) -> None:
    raise AnalysisValidationError(AnalysisValidationCode.INVALID_SCHEMA, detail)


def _duplicate(detail: str) -> None:
    raise AnalysisValidationError(AnalysisValidationCode.DUPLICATE_IDENTIFIER, detail)
