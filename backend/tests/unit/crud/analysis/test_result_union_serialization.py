from dataclasses import replace

import pytest
from app.crud.analysis_repository_serialization import (
    analysis_result_document,
    analysis_result_from_document,
)
from app.services.analysis.rules.enums import AnalysisResultKind
from app.services.analysis.rules.result_models import AnalysisMedia
from app.services.analysis.rules.result_types import AnalysisResult
from app.services.analysis.rules.video_article_parser import parse_video_article_result
from tests.unit.crud.analysis.factories import analysis_result
from tests.unit.services.analysis.rules.screenplay_factories import (
    screenplay_analysis_result,
    screenplay_rewrite_result,
)
from tests.unit.services.analysis.rules.test_video_article import article_payload


@pytest.mark.parametrize(
    ("result", "kind"),
    [
        (analysis_result(), AnalysisResultKind.VIDEO_VISUAL_ANALYSIS.value),
        (screenplay_analysis_result(), AnalysisResultKind.SCREENPLAY_ANALYSIS.value),
        (screenplay_rewrite_result(), AnalysisResultKind.SCREENPLAY_REWRITE.value),
        (
            parse_video_article_result(
                article_payload(),
                AnalysisMedia(duration_ms=3_000, container="mp4", size_bytes=1_024),
                expected_language="zh-CN",
            ),
            AnalysisResultKind.VIDEO_ARTICLE.value,
        ),
    ],
)
def test_current_results_round_trip_with_kind(
    result: AnalysisResult, kind: str
) -> None:
    document = analysis_result_document(result)

    assert document["kind"] == kind
    assert analysis_result_from_document(document) == result


def test_stored_result_without_kind_has_no_legacy_parser() -> None:
    document = analysis_result_document(analysis_result())
    document.pop("kind")

    with pytest.raises(ValueError, match="unknown kind"):
        analysis_result_from_document(document)


def test_stored_screenplay_result_rejects_unknown_fields() -> None:
    document = analysis_result_document(screenplay_analysis_result())
    scene = document["scenes"][0]
    assert isinstance(scene, dict)
    scene["unexpected"] = True

    with pytest.raises(ValueError, match="invalid shape"):
        analysis_result_from_document(document)


def test_result_kind_is_immutable() -> None:
    result = screenplay_analysis_result()

    with pytest.raises(ValueError, match="init=False"):
        replace(result, kind=AnalysisResultKind.SCREENPLAY_REWRITE)
