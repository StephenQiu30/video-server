from app.domain.analysis import (
    AnalysisMedia,
    AnalysisResultKind,
    VideoArticleEvidence,
    VideoArticleResult,
    VideoArticleSection,
)
from app.infrastructure.analysis_storage_fields import (
    array,
    integer,
    mapping,
    string,
    strings,
)

_FIELDS = {
    "kind",
    "language",
    "title",
    "lead",
    "sections",
    "key_points",
    "closing",
    "limitations",
    "media",
}


def video_article_from_document(document: object) -> VideoArticleResult:
    root = mapping(document, _FIELDS, "video article result")
    if root["kind"] != AnalysisResultKind.VIDEO_ARTICLE.value:
        raise ValueError("stored video article kind is invalid")
    media = mapping(root["media"], {"duration_ms", "container", "size_bytes"}, "media")
    return VideoArticleResult(
        language=string(root["language"], "language"),
        title=string(root["title"], "title"),
        lead=string(root["lead"], "lead"),
        sections=tuple(_section(item) for item in array(root["sections"], "sections")),
        key_points=tuple(strings(root["key_points"], "key_points")),
        closing=string(root["closing"], "closing"),
        limitations=tuple(strings(root["limitations"], "limitations")),
        media=AnalysisMedia(
            duration_ms=integer(media["duration_ms"], "media.duration_ms"),
            container=string(media["container"], "media.container"),
            size_bytes=integer(media["size_bytes"], "media.size_bytes"),
        ),
    )


def _section(value: object) -> VideoArticleSection:
    source = mapping(value, {"id", "title", "body", "evidence"}, "article section")
    return VideoArticleSection(
        id=string(source["id"], "article section.id"),
        title=string(source["title"], "article section.title"),
        body=string(source["body"], "article section.body"),
        evidence=tuple(
            _evidence(item) for item in array(source["evidence"], "article evidence")
        ),
    )


def _evidence(value: object) -> VideoArticleEvidence:
    source = mapping(value, {"start_ms", "end_ms", "note"}, "article evidence")
    return VideoArticleEvidence(
        start_ms=integer(source["start_ms"], "article evidence.start_ms"),
        end_ms=integer(source["end_ms"], "article evidence.end_ms"),
        note=string(source["note"], "article evidence.note"),
    )
