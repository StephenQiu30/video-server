from __future__ import annotations

from app.domain.analysis.parse_helpers import ParseContext
from app.domain.analysis.result_items import Highlight, Shot, VisualAsset
from app.domain.analysis.result_models import ProductionAdvice
from app.domain.analysis.video_scene import VideoScene


def parse_shot(context: ParseContext, value: object, index: int) -> Shot:
    path = f"shots[{index}]"
    source = context.mapping(
        value,
        path,
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
        },
    )
    return Shot(
        id=context.text(source["id"], f"{path}.id", maximum=128),
        index=context.integer(source["index"], f"{path}.index"),
        start_ms=context.integer(source["start_ms"], f"{path}.start_ms"),
        end_ms=context.integer(source["end_ms"], f"{path}.end_ms"),
        representative_frame_ms=context.integer(
            source["representative_frame_ms"],
            f"{path}.representative_frame_ms",
        ),
        description=context.text(source["description"], f"{path}.description"),
        transition_in=context.text(
            source["transition_in"], f"{path}.transition_in", maximum=32
        ),
        shot_size=context.text(source["shot_size"], f"{path}.shot_size", maximum=32),
        camera_motion=context.text(
            source["camera_motion"], f"{path}.camera_motion", maximum=32
        ),
        narrative_function=context.text(
            source["narrative_function"], f"{path}.narrative_function"
        ),
        highlight_score=context.integer(
            source["highlight_score"], f"{path}.highlight_score"
        ),
        visual_tags=_strings(context, source["visual_tags"], f"{path}.visual_tags"),
        asset_ids=(),
    )


def parse_highlight(context: ParseContext, value: object, index: int) -> Highlight:
    path = f"highlights[{index}]"
    source = context.mapping(
        value,
        path,
        {"id", "title", "description", "score", "reason", "evidence_shot_ids"},
    )
    return Highlight(
        id=context.text(source["id"], f"{path}.id", maximum=128),
        title=context.text(source["title"], f"{path}.title"),
        description=context.text(source["description"], f"{path}.description"),
        score=context.integer(source["score"], f"{path}.score"),
        reason=context.text(source["reason"], f"{path}.reason"),
        start_ms=0,
        end_ms=1,
        evidence_shot_ids=evidence_ids(
            context, source["evidence_shot_ids"], f"{path}.evidence_shot_ids"
        ),
    )


def parse_scene(context: ParseContext, value: object, index: int) -> VideoScene:
    path = f"scenes[{index}]"
    source = context.mapping(
        value,
        path,
        {
            "id",
            "index",
            "title",
            "location",
            "description",
            "narrative_function",
            "visual_rules",
            "continuity_risks",
            "evidence_shot_ids",
        },
    )
    return VideoScene(
        id=context.text(source["id"], f"{path}.id", maximum=128),
        index=context.integer(source["index"], f"{path}.index"),
        title=context.text(source["title"], f"{path}.title"),
        start_ms=0,
        end_ms=1,
        location=context.text(source["location"], f"{path}.location"),
        description=context.text(source["description"], f"{path}.description"),
        narrative_function=context.text(
            source["narrative_function"], f"{path}.narrative_function"
        ),
        visual_rules=_strings(context, source["visual_rules"], f"{path}.visual_rules"),
        continuity_risks=_strings(
            context, source["continuity_risks"], f"{path}.continuity_risks"
        ),
        evidence_shot_ids=evidence_ids(
            context, source["evidence_shot_ids"], f"{path}.evidence_shot_ids"
        ),
    )


def parse_asset(context: ParseContext, value: object, index: int) -> VisualAsset:
    path = f"assets[{index}]"
    source = context.mapping(
        value,
        path,
        {"id", "type", "label", "description", "evidence_shot_ids"},
    )
    return VisualAsset(
        id=context.text(source["id"], f"{path}.id", maximum=128),
        type=context.text(source["type"], f"{path}.type", maximum=32),
        label=context.text(source["label"], f"{path}.label"),
        description=context.text(source["description"], f"{path}.description"),
        first_seen_ms=0,
        evidence_shot_ids=evidence_ids(
            context, source["evidence_shot_ids"], f"{path}.evidence_shot_ids"
        ),
    )


def evidence_ids(context: ParseContext, value: object, path: str) -> tuple[str, ...]:
    return tuple(
        context.text(item, f"{path}[{index}]", maximum=128)
        for index, item in enumerate(context.array(value, path, allow_empty=False))
    )


def parse_production_advice(context: ParseContext, value: object) -> ProductionAdvice:
    path = "production_advice"
    source = context.mapping(
        value,
        path,
        {"summary", "priority_shot_ids", "recommended_extensions"},
    )
    return ProductionAdvice(
        summary=context.text(source["summary"], f"{path}.summary"),
        priority_shot_ids=evidence_ids(
            context, source["priority_shot_ids"], f"{path}.priority_shot_ids"
        ),
        recommended_extensions=_strings(
            context,
            source["recommended_extensions"],
            f"{path}.recommended_extensions",
        ),
    )


def _strings(context: ParseContext, value: object, path: str) -> tuple[str, ...]:
    return tuple(
        context.text(item, f"{path}[{index}]", maximum=128)
        for index, item in enumerate(context.array(value, path, allow_empty=True))
    )
