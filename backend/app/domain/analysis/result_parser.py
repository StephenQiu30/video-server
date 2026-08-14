from __future__ import annotations

from app.domain.analysis.enums import AnalysisValidationCode
from app.domain.analysis.errors import AnalysisValidationError
from app.domain.analysis.parse_helpers import ParseContext
from app.domain.analysis.result_drafts import (
    evidence_ids,
    parse_asset,
    parse_highlight,
    parse_production_advice,
    parse_shot,
)
from app.domain.analysis.result_items import Highlight, Shot, VisualAsset
from app.domain.analysis.result_models import (
    AnalysisLimits,
    AnalysisMedia,
    EvidenceSummary,
    VideoAnalysisResult,
)
from app.domain.analysis.result_validation import validate_analysis_result


def parse_analysis_result(
    payload: object,
    media: AnalysisMedia,
    *,
    expected_language: str,
    limits: AnalysisLimits | None = None,
) -> VideoAnalysisResult:
    context = ParseContext(limits or AnalysisLimits())
    root = context.mapping(
        payload,
        "result",
        {
            "language",
            "title",
            "summary",
            "shots",
            "highlights",
            "assets",
            "production_advice",
        },
    )
    language = context.text(root["language"], "language", maximum=35)
    if language != expected_language:
        raise AnalysisValidationError(
            AnalysisValidationCode.INVALID_SCHEMA,
            "output language does not match the job",
        )

    shot_drafts = tuple(
        parse_shot(context, value, index)
        for index, value in enumerate(
            context.array(root["shots"], "shots", allow_empty=False)
        )
    )
    highlight_drafts = tuple(
        parse_highlight(context, value, index)
        for index, value in enumerate(
            context.array(root["highlights"], "highlights", allow_empty=True)
        )
    )
    asset_drafts = tuple(
        parse_asset(context, value, index)
        for index, value in enumerate(
            context.array(root["assets"], "assets", allow_empty=True)
        )
    )
    shot_by_id = {shot.id: shot for shot in shot_drafts}
    assets = tuple(
        VisualAsset(
            id=item.id,
            type=item.type,
            label=item.label,
            description=item.description,
            first_seen_ms=_first_seen(item.evidence_shot_ids, shot_by_id),
            evidence_shot_ids=item.evidence_shot_ids,
        )
        for item in asset_drafts
    )
    shots = tuple(
        Shot(
            id=item.id,
            index=item.index,
            start_ms=item.start_ms,
            end_ms=item.end_ms,
            representative_frame_ms=item.representative_frame_ms,
            description=item.description,
            transition_in=item.transition_in,
            shot_size=item.shot_size,
            camera_motion=item.camera_motion,
            narrative_function=item.narrative_function,
            highlight_score=item.highlight_score,
            visual_tags=item.visual_tags,
            asset_ids=tuple(
                asset.id for asset in assets if item.id in asset.evidence_shot_ids
            ),
        )
        for item in shot_drafts
    )
    highlights = tuple(
        Highlight(
            id=item.id,
            title=item.title,
            description=item.description,
            score=item.score,
            reason=item.reason,
            start_ms=_first_seen(item.evidence_shot_ids, shot_by_id),
            end_ms=_last_seen(item.evidence_shot_ids, shot_by_id),
            evidence_shot_ids=item.evidence_shot_ids,
        )
        for item in highlight_drafts
    )
    result = VideoAnalysisResult(
        language=language,
        title=context.text(root["title"], "title"),
        summary=_summary(context, root["summary"]),
        media=media,
        shot_count=len(shots),
        shots=shots,
        highlights=highlights,
        assets=assets,
        production_advice=parse_production_advice(context, root["production_advice"]),
    )
    validate_analysis_result(result, limits=context.limits)
    return result


def _summary(context: ParseContext, value: object) -> EvidenceSummary:
    source = context.mapping(value, "summary", {"text", "evidence_shot_ids"})
    return EvidenceSummary(
        text=context.text(source["text"], "summary.text"),
        evidence_shot_ids=evidence_ids(
            context, source["evidence_shot_ids"], "summary.evidence_shot_ids"
        ),
    )


def _first_seen(references: tuple[str, ...], shots: dict[str, Shot]) -> int:
    return min(_referenced(references, shots), key=lambda shot: shot.start_ms).start_ms


def _last_seen(references: tuple[str, ...], shots: dict[str, Shot]) -> int:
    return max(_referenced(references, shots), key=lambda shot: shot.end_ms).end_ms


def _referenced(
    references: tuple[str, ...], shots: dict[str, Shot]
) -> tuple[Shot, ...]:
    try:
        return tuple(shots[shot_id] for shot_id in references)
    except KeyError as exc:
        raise AnalysisValidationError(
            AnalysisValidationCode.INVALID_EVIDENCE,
            f"unknown evidence shot id: {exc.args[0]}",
        ) from exc
