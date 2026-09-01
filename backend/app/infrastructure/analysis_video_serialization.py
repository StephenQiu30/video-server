from app.domain.analysis import (
    AnalysisMedia,
    AnalysisResultKind,
    EvidenceSummary,
    VideoAnalysisResult,
    validate_analysis_result,
)
from app.infrastructure.analysis_storage_fields import (
    array,
    integer,
    mapping,
    string,
    strings,
)
from app.infrastructure.analysis_video_serialization_items import (
    stored_asset,
    stored_highlight,
    stored_production_advice,
    stored_scene,
    stored_shot,
)

_FIELDS = {
    "kind",
    "language",
    "title",
    "summary",
    "media",
    "shot_count",
    "shots",
    "scenes",
    "highlights",
    "assets",
    "production_advice",
}


def video_result_from_document(document: object) -> VideoAnalysisResult:
    root = mapping(document, _FIELDS, "video analysis result")
    if root["kind"] != AnalysisResultKind.VIDEO_VISUAL_ANALYSIS.value:
        raise ValueError("stored video analysis kind is invalid")
    summary = mapping(root["summary"], {"text", "evidence_shot_ids"}, "summary")
    media = mapping(root["media"], {"duration_ms", "container", "size_bytes"}, "media")
    result = VideoAnalysisResult(
        language=string(root["language"], "language"),
        title=string(root["title"], "title"),
        summary=EvidenceSummary(
            text=string(summary["text"], "summary.text"),
            evidence_shot_ids=strings(
                summary["evidence_shot_ids"], "summary.evidence_shot_ids"
            ),
        ),
        media=AnalysisMedia(
            duration_ms=integer(media["duration_ms"], "media.duration_ms"),
            container=string(media["container"], "media.container"),
            size_bytes=integer(media["size_bytes"], "media.size_bytes"),
        ),
        shot_count=integer(root["shot_count"], "shot_count"),
        shots=tuple(stored_shot(value) for value in array(root["shots"], "shots")),
        scenes=tuple(stored_scene(value) for value in array(root["scenes"], "scenes")),
        highlights=tuple(
            stored_highlight(value) for value in array(root["highlights"], "highlights")
        ),
        assets=tuple(stored_asset(value) for value in array(root["assets"], "assets")),
        production_advice=stored_production_advice(root["production_advice"]),
    )
    validate_analysis_result(result)
    return result
