"""Strict current-state serialization for every analysis result contract."""

from typing import Any

from app.domain.analysis import (
    AnalysisResult,
    AnalysisResultKind,
    ScreenplayAnalysisResult,
    ScreenplayRewriteResult,
    VideoAnalysisResult,
    VideoArticleResult,
)
from app.infrastructure.analysis_screenplay_rewrite_serialization import (
    screenplay_rewrite_from_document,
)
from app.infrastructure.analysis_screenplay_serialization import (
    screenplay_analysis_from_document,
)
from app.infrastructure.analysis_storage_fields import dataclass_document, mapping
from app.infrastructure.analysis_video_article_serialization import (
    video_article_from_document,
)
from app.infrastructure.analysis_video_serialization import video_result_from_document


def analysis_result_document(result: AnalysisResult) -> dict[str, Any]:
    result_kind(result)
    return dataclass_document(result)


def analysis_result_from_document(document: object) -> AnalysisResult:
    root = mapping(document, None, "analysis result")
    kind = root.get("kind")
    if kind == AnalysisResultKind.VIDEO_VISUAL_ANALYSIS.value:
        return video_result_from_document(root)
    if kind == AnalysisResultKind.VIDEO_ARTICLE.value:
        return video_article_from_document(root)
    if kind == AnalysisResultKind.SCREENPLAY_ANALYSIS.value:
        return screenplay_analysis_from_document(root)
    if kind == AnalysisResultKind.SCREENPLAY_REWRITE.value:
        return screenplay_rewrite_from_document(root)
    raise ValueError("stored analysis result has an unknown kind")


def result_kind(result: AnalysisResult) -> AnalysisResultKind:
    if isinstance(result, VideoAnalysisResult):
        return AnalysisResultKind.VIDEO_VISUAL_ANALYSIS
    if isinstance(result, VideoArticleResult):
        return AnalysisResultKind.VIDEO_ARTICLE
    if isinstance(result, ScreenplayAnalysisResult):
        return AnalysisResultKind.SCREENPLAY_ANALYSIS
    if isinstance(result, ScreenplayRewriteResult):
        return AnalysisResultKind.SCREENPLAY_REWRITE
    raise TypeError("unsupported analysis result")
