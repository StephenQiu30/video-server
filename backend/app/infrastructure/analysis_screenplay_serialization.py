from app.domain.analysis import (
    AnalysisResultKind,
    ScreenplayAnalysisResult,
    ScreenplayCharacter,
    ScreenplayEvidenceItem,
    ScreenplayScene,
    ScreenplayStructure,
)
from app.infrastructure.analysis_storage_fields import array, mapping, string, strings

_FIELDS = {
    "kind",
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
}


def screenplay_analysis_from_document(document: object) -> ScreenplayAnalysisResult:
    root = mapping(document, _FIELDS, "screenplay analysis result")
    if root["kind"] != AnalysisResultKind.SCREENPLAY_ANALYSIS.value:
        raise ValueError("stored screenplay analysis kind is invalid")
    structure = mapping(
        root["structure"], {"acts", "turning_points", "pacing_summary"}, "structure"
    )
    return ScreenplayAnalysisResult(
        language=string(root["language"], "language"),
        title=string(root["title"], "title"),
        logline=string(root["logline"], "logline"),
        synopsis=string(root["synopsis"], "synopsis"),
        structure=ScreenplayStructure(
            acts=tuple(
                _evidence_item(value, "act")
                for value in array(structure["acts"], "structure.acts")
            ),
            turning_points=tuple(
                _evidence_item(value, "turning point")
                for value in array(
                    structure["turning_points"], "structure.turning_points"
                )
            ),
            pacing_summary=string(
                structure["pacing_summary"], "structure.pacing_summary"
            ),
        ),
        characters=tuple(
            _character(value) for value in array(root["characters"], "characters")
        ),
        scenes=tuple(_scene(value) for value in array(root["scenes"], "scenes")),
        dialogue_findings=_evidence_items(
            root["dialogue_findings"], "dialogue finding"
        ),
        strengths=_evidence_items(root["strengths"], "strength"),
        priority_revisions=_evidence_items(
            root["priority_revisions"], "priority revision"
        ),
    )


def _evidence_items(value: object, label: str) -> tuple[ScreenplayEvidenceItem, ...]:
    return tuple(_evidence_item(item, label) for item in array(value, f"{label}s"))


def _evidence_item(value: object, label: str) -> ScreenplayEvidenceItem:
    source = mapping(value, {"id", "title", "description", "evidence_scene_ids"}, label)
    return ScreenplayEvidenceItem(
        id=string(source["id"], f"{label}.id"),
        title=string(source["title"], f"{label}.title"),
        description=string(source["description"], f"{label}.description"),
        evidence_scene_ids=strings(
            source["evidence_scene_ids"], f"{label}.evidence_scene_ids"
        ),
    )


def _character(value: object) -> ScreenplayCharacter:
    source = mapping(
        value,
        {"id", "name", "goal", "conflict", "arc", "evidence_scene_ids"},
        "character",
    )
    return ScreenplayCharacter(
        id=string(source["id"], "character.id"),
        name=string(source["name"], "character.name"),
        goal=string(source["goal"], "character.goal"),
        conflict=string(source["conflict"], "character.conflict"),
        arc=string(source["arc"], "character.arc"),
        evidence_scene_ids=strings(
            source["evidence_scene_ids"], "character.evidence_scene_ids"
        ),
    )


def _scene(value: object) -> ScreenplayScene:
    source = mapping(
        value,
        {"id", "source_scene_id", "purpose", "conflict", "turn", "pacing", "findings"},
        "scene",
    )
    return ScreenplayScene(
        id=string(source["id"], "scene.id"),
        source_scene_id=string(source["source_scene_id"], "scene.source_scene_id"),
        purpose=string(source["purpose"], "scene.purpose"),
        conflict=string(source["conflict"], "scene.conflict"),
        turn=string(source["turn"], "scene.turn"),
        pacing=string(source["pacing"], "scene.pacing"),
        findings=strings(source["findings"], "scene.findings"),
    )
