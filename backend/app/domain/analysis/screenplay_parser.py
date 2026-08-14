from __future__ import annotations

from app.domain.analysis.enums import AnalysisValidationCode
from app.domain.analysis.errors import AnalysisValidationError
from app.domain.analysis.parse_helpers import ParseContext
from app.domain.analysis.result_models import AnalysisLimits
from app.domain.analysis.screenplay_result_items import (
    ScreenplayCharacter,
    ScreenplayEvidenceItem,
    ScreenplayScene,
    ScreenplayStructure,
)
from app.domain.analysis.screenplay_results import ScreenplayAnalysisResult


def parse_screenplay_analysis_result(
    payload: object,
    *,
    expected_language: str,
    source_scene_ids: tuple[str, ...],
    limits: AnalysisLimits | None = None,
) -> ScreenplayAnalysisResult:
    if not source_scene_ids or len(set(source_scene_ids)) != len(source_scene_ids):
        raise ValueError("source scene ids must be non-empty and unique")
    context = ParseContext(limits or AnalysisLimits())
    root = context.mapping(
        payload,
        "result",
        {
            "language",
            "title",
            "logline",
            "synopsis",
            "structure",
            "characters",
            "scenes",
            "dialogue_findings",
            "strengths",
            "priority_revisions",
        },
    )
    language = context.text(root["language"], "language", maximum=35)
    if language != expected_language:
        _invalid("output language does not match the job")
    structure = context.mapping(
        root["structure"],
        "structure",
        {"acts", "turning_points", "pacing_summary"},
    )
    result = ScreenplayAnalysisResult(
        language=language,
        title=context.text(root["title"], "title"),
        logline=context.text(root["logline"], "logline"),
        synopsis=context.text(root["synopsis"], "synopsis"),
        structure=ScreenplayStructure(
            acts=_evidence_items(context, structure["acts"], "act", False),
            turning_points=_evidence_items(
                context, structure["turning_points"], "turning_point", True
            ),
            pacing_summary=context.text(
                structure["pacing_summary"], "structure.pacing_summary"
            ),
        ),
        characters=tuple(
            _character(context, value, index)
            for index, value in enumerate(
                context.array(root["characters"], "characters", allow_empty=True)
            )
        ),
        scenes=tuple(
            _scene(context, value, index)
            for index, value in enumerate(
                context.array(root["scenes"], "scenes", allow_empty=False)
            )
        ),
        dialogue_findings=_evidence_items(
            context, root["dialogue_findings"], "dialogue_finding", True
        ),
        strengths=_evidence_items(context, root["strengths"], "strength", False),
        priority_revisions=_evidence_items(
            context, root["priority_revisions"], "priority_revision", False
        ),
    )
    actual_scene_ids = tuple(scene.source_scene_id for scene in result.scenes)
    if actual_scene_ids != source_scene_ids:
        raise AnalysisValidationError(
            AnalysisValidationCode.INVALID_EVIDENCE,
            "screenplay result must cover source scenes exactly once and in order",
        )
    return result


def _evidence_items(
    context: ParseContext, value: object, label: str, allow_empty: bool
) -> tuple[ScreenplayEvidenceItem, ...]:
    return tuple(
        _evidence_item(context, item, f"{label}[{index}]")
        for index, item in enumerate(
            context.array(value, label, allow_empty=allow_empty)
        )
    )


def _evidence_item(
    context: ParseContext, value: object, path: str
) -> ScreenplayEvidenceItem:
    source = context.mapping(
        value, path, {"id", "title", "description", "evidence_scene_ids"}
    )
    return ScreenplayEvidenceItem(
        id=context.text(source["id"], f"{path}.id", maximum=128),
        title=context.text(source["title"], f"{path}.title"),
        description=context.text(source["description"], f"{path}.description"),
        evidence_scene_ids=_references(
            context, source["evidence_scene_ids"], f"{path}.evidence_scene_ids"
        ),
    )


def _character(context: ParseContext, value: object, index: int) -> ScreenplayCharacter:
    path = f"character[{index}]"
    source = context.mapping(
        value, path, {"id", "name", "goal", "conflict", "arc", "evidence_scene_ids"}
    )
    return ScreenplayCharacter(
        id=context.text(source["id"], f"{path}.id", maximum=128),
        name=context.text(source["name"], f"{path}.name"),
        goal=context.text(source["goal"], f"{path}.goal"),
        conflict=context.text(source["conflict"], f"{path}.conflict"),
        arc=context.text(source["arc"], f"{path}.arc"),
        evidence_scene_ids=_references(
            context, source["evidence_scene_ids"], f"{path}.evidence_scene_ids"
        ),
    )


def _scene(context: ParseContext, value: object, index: int) -> ScreenplayScene:
    path = f"scene[{index}]"
    source = context.mapping(
        value,
        path,
        {"id", "source_scene_id", "purpose", "conflict", "turn", "pacing", "findings"},
    )
    return ScreenplayScene(
        id=context.text(source["id"], f"{path}.id", maximum=128),
        source_scene_id=context.text(
            source["source_scene_id"], f"{path}.source_scene_id", maximum=128
        ),
        purpose=context.text(source["purpose"], f"{path}.purpose"),
        conflict=context.text(source["conflict"], f"{path}.conflict"),
        turn=context.text(source["turn"], f"{path}.turn"),
        pacing=context.text(source["pacing"], f"{path}.pacing"),
        findings=tuple(
            context.text(item, f"{path}.findings")
            for item in context.array(
                source["findings"], f"{path}.findings", allow_empty=True
            )
        ),
    )


def _references(context: ParseContext, value: object, path: str) -> tuple[str, ...]:
    return tuple(
        context.text(item, path, maximum=128)
        for item in context.array(value, path, allow_empty=False)
    )


def _invalid(detail: str) -> None:
    raise AnalysisValidationError(AnalysisValidationCode.INVALID_SCHEMA, detail)
