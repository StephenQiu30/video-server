from app.domain.analysis.enums import AnalysisResultContract
from app.domain.analysis.result_models import VideoAnalysisResult, VideoArticleResult
from app.domain.analysis.screenplay_results import (
    ScreenplayAnalysisResult,
    ScreenplayRewriteResult,
)

type AnalysisResult = (
    VideoAnalysisResult
    | VideoArticleResult
    | ScreenplayAnalysisResult
    | ScreenplayRewriteResult
)


def analysis_result_contract(result: AnalysisResult) -> AnalysisResultContract:
    if isinstance(result, VideoAnalysisResult):
        return AnalysisResultContract.VIDEO_VISUAL_ANALYSIS
    if isinstance(result, VideoArticleResult):
        return AnalysisResultContract.VIDEO_ARTICLE
    if isinstance(result, ScreenplayAnalysisResult):
        return AnalysisResultContract.SCREENPLAY_ANALYSIS
    return AnalysisResultContract.SCREENPLAY_REWRITE


def analysis_result_language(result: AnalysisResult) -> str:
    if isinstance(result, ScreenplayRewriteResult):
        return result.target_language
    return result.language
