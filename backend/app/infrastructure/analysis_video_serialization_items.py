from app.domain.analysis import (
    Highlight,
    ProductionAdvice,
    Shot,
    VideoScene,
    VisualAsset,
)
from app.infrastructure.analysis_storage_fields import integer, mapping, string, strings


def stored_shot(value: object) -> Shot:
    source = mapping(
        value,
        {
            "id",
            "index",
            "start_ms",
            "end_ms",
            "representative_frame_ms",
            "description",
            "transition_in",
            "shot_size",
            "camera_motion",
            "narrative_function",
            "highlight_score",
            "visual_tags",
            "asset_ids",
        },
        "shot",
    )
    return Shot(
        id=string(source["id"], "shot.id"),
        index=integer(source["index"], "shot.index"),
        start_ms=integer(source["start_ms"], "shot.start_ms"),
        end_ms=integer(source["end_ms"], "shot.end_ms"),
        representative_frame_ms=integer(
            source["representative_frame_ms"], "shot.representative_frame_ms"
        ),
        description=string(source["description"], "shot.description"),
        transition_in=string(source["transition_in"], "shot.transition_in"),
        shot_size=string(source["shot_size"], "shot.shot_size"),
        camera_motion=string(source["camera_motion"], "shot.camera_motion"),
        narrative_function=string(
            source["narrative_function"], "shot.narrative_function"
        ),
        highlight_score=integer(source["highlight_score"], "shot.highlight_score"),
        visual_tags=strings(source["visual_tags"], "shot.visual_tags"),
        asset_ids=strings(source["asset_ids"], "shot.asset_ids"),
    )


def stored_highlight(value: object) -> Highlight:
    source = mapping(
        value,
        {
            "id",
            "title",
            "description",
            "score",
            "reason",
            "start_ms",
            "end_ms",
            "evidence_shot_ids",
        },
        "highlight",
    )
    return Highlight(
        id=string(source["id"], "highlight.id"),
        title=string(source["title"], "highlight.title"),
        description=string(source["description"], "highlight.description"),
        score=integer(source["score"], "highlight.score"),
        reason=string(source["reason"], "highlight.reason"),
        start_ms=integer(source["start_ms"], "highlight.start_ms"),
        end_ms=integer(source["end_ms"], "highlight.end_ms"),
        evidence_shot_ids=strings(
            source["evidence_shot_ids"], "highlight.evidence_shot_ids"
        ),
    )


def stored_scene(value: object) -> VideoScene:
    source = mapping(
        value,
        {
            "id",
            "index",
            "title",
            "start_ms",
            "end_ms",
            "location",
            "description",
            "narrative_function",
            "visual_rules",
            "continuity_risks",
            "evidence_shot_ids",
        },
        "scene",
    )
    return VideoScene(
        id=string(source["id"], "scene.id"),
        index=integer(source["index"], "scene.index"),
        title=string(source["title"], "scene.title"),
        start_ms=integer(source["start_ms"], "scene.start_ms"),
        end_ms=integer(source["end_ms"], "scene.end_ms"),
        location=string(source["location"], "scene.location"),
        description=string(source["description"], "scene.description"),
        narrative_function=string(
            source["narrative_function"], "scene.narrative_function"
        ),
        visual_rules=strings(source["visual_rules"], "scene.visual_rules"),
        continuity_risks=strings(source["continuity_risks"], "scene.continuity_risks"),
        evidence_shot_ids=strings(
            source["evidence_shot_ids"], "scene.evidence_shot_ids"
        ),
    )


def stored_asset(value: object) -> VisualAsset:
    source = mapping(
        value,
        {"id", "type", "label", "description", "first_seen_ms", "evidence_shot_ids"},
        "asset",
    )
    return VisualAsset(
        id=string(source["id"], "asset.id"),
        type=string(source["type"], "asset.type"),
        label=string(source["label"], "asset.label"),
        description=string(source["description"], "asset.description"),
        first_seen_ms=integer(source["first_seen_ms"], "asset.first_seen_ms"),
        evidence_shot_ids=strings(
            source["evidence_shot_ids"], "asset.evidence_shot_ids"
        ),
    )


def stored_production_advice(value: object) -> ProductionAdvice:
    source = mapping(
        value,
        {"summary", "priority_shot_ids", "recommended_extensions"},
        "production advice",
    )
    return ProductionAdvice(
        summary=string(source["summary"], "production_advice.summary"),
        priority_shot_ids=strings(
            source["priority_shot_ids"], "production_advice.priority_shot_ids"
        ),
        recommended_extensions=strings(
            source["recommended_extensions"],
            "production_advice.recommended_extensions",
        ),
    )
