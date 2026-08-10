from __future__ import annotations

from typing import Protocol

from app.domain.analysis.enums import AnalysisValidationCode
from app.domain.analysis.errors import AnalysisValidationError
from app.domain.analysis.result_models import AnalysisLimits, AnalysisResult

TRANSITIONS = {"cut", "fade", "dissolve", "wipe", "none", "unknown"}
SHOT_SIZES = {
    "extreme_wide",
    "wide",
    "medium",
    "close_up",
    "extreme_close_up",
    "mixed",
    "unknown",
}
CAMERA_MOTIONS = {
    "static",
    "pan",
    "tilt",
    "zoom",
    "dolly",
    "tracking",
    "handheld",
    "mixed",
    "unknown",
}
ASSET_TYPES = {"person", "location", "object", "product", "logo", "on_screen_text"}


def validate_analysis_result(
    result: AnalysisResult,
    *,
    limits: AnalysisLimits | None = None,
) -> None:
    limits = limits or AnalysisLimits()
    collections = (result.shots, result.highlights, result.assets)
    if any(len(collection) > limits.max_collection_items for collection in collections):
        raise AnalysisValidationError(
            AnalysisValidationCode.LIMIT_EXCEEDED,
            "analysis collection exceeds the configured item limit",
        )

    shot_by_id = _unique(result.shots, "shot")
    _unique(result.highlights, "highlight")
    asset_by_id = _unique(result.assets, "asset")

    previous_end = 0
    for expected_index, shot in enumerate(result.shots, start=1):
        if shot.index != expected_index or shot.start_ms != previous_end:
            _invalid_time("shots must be a continuous ordered partition")
        if shot.transition_in not in TRANSITIONS:
            _invalid_schema("shot transition is unsupported")
        if shot.shot_size not in SHOT_SIZES:
            _invalid_schema("shot size is unsupported")
        if shot.camera_motion not in CAMERA_MOTIONS:
            _invalid_schema("camera motion is unsupported")
        if any(asset_id not in asset_by_id for asset_id in shot.asset_ids):
            _invalid_evidence("shot references an unknown asset")
        previous_end = shot.end_ms
    if result.shots[0].transition_in != "none":
        _invalid_schema("the first shot transition_in must be none")
    if previous_end != result.media.duration_ms:
        _invalid_time("shots must end at the authoritative media duration")

    _shot_refs(result.summary.evidence_shot_ids, shot_by_id)
    _shot_refs(result.production_advice.priority_shot_ids, shot_by_id)
    for highlight in result.highlights:
        evidence = _shot_refs(highlight.evidence_shot_ids, shot_by_id)
        if highlight.start_ms != min(item.start_ms for item in evidence):
            _invalid_time("highlight start must match its earliest evidence")
        if highlight.end_ms != max(item.end_ms for item in evidence):
            _invalid_time("highlight end must match its latest evidence")
    for asset in result.assets:
        if asset.type not in ASSET_TYPES:
            _invalid_schema("asset type is unsupported")
        evidence = _shot_refs(asset.evidence_shot_ids, shot_by_id)
        if asset.first_seen_ms != min(item.start_ms for item in evidence):
            _invalid_time("asset first_seen_ms must match its earliest evidence")
        reverse = tuple(shot.id for shot in result.shots if asset.id in shot.asset_ids)
        if reverse != asset.evidence_shot_ids:
            _invalid_evidence("shot asset index differs from asset evidence")


class _Identified(Protocol):
    @property
    def id(self) -> str: ...


def _unique[ItemT: _Identified](
    values: tuple[ItemT, ...], label: str
) -> dict[str, ItemT]:
    result: dict[str, ItemT] = {}
    for value in values:
        identifier = value.id
        if identifier in result:
            raise AnalysisValidationError(
                AnalysisValidationCode.DUPLICATE_IDENTIFIER,
                f"{label} ids must be unique",
            )
        result[identifier] = value
    return result


def _shot_refs[ShotT](
    references: tuple[str, ...], shots: dict[str, ShotT]
) -> tuple[ShotT, ...]:
    try:
        return tuple(shots[shot_id] for shot_id in references)
    except KeyError as exc:
        raise AnalysisValidationError(
            AnalysisValidationCode.INVALID_EVIDENCE,
            f"unknown evidence shot id: {exc.args[0]}",
        ) from exc


def _invalid_schema(detail: str) -> None:
    raise AnalysisValidationError(AnalysisValidationCode.INVALID_SCHEMA, detail)


def _invalid_time(detail: str) -> None:
    raise AnalysisValidationError(AnalysisValidationCode.INVALID_TIME_RANGE, detail)


def _invalid_evidence(detail: str) -> None:
    raise AnalysisValidationError(AnalysisValidationCode.INVALID_EVIDENCE, detail)
