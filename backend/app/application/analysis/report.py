from __future__ import annotations

from app.application.analysis.report_formatting import (
    format_range as _format_range,
)
from app.application.analysis.report_formatting import (
    format_size as _format_size,
)
from app.application.analysis.report_formatting import (
    format_time as _format_time,
)
from app.application.analysis.report_formatting import (
    markdown_block as _markdown_block,
)
from app.application.analysis.report_formatting import (
    markdown_text as _markdown_text,
)
from app.application.analysis.screenplay_report import render_screenplay_report_markdown
from app.application.analysis.video_report import render_video_analysis_report_markdown
from app.application.analysis.video_report_labels import video_report_labels as _labels
from app.domain.analysis import AnalysisResult, VideoAnalysisResult, VideoArticleResult


def render_analysis_report_markdown(result: AnalysisResult) -> str:
    if isinstance(result, VideoArticleResult):
        return _render_video_article_report_markdown(result)
    if not isinstance(result, VideoAnalysisResult):
        return render_screenplay_report_markdown(result)
    return render_video_analysis_report_markdown(result)


def _render_video_article_report_markdown(result: VideoArticleResult) -> str:
    lines = [
        f"# {_markdown_text(result.title)}",
        "",
        _markdown_block(result.lead),
        "",
    ]
    for index, section in enumerate(result.sections, start=1):
        lines.extend(
            (
                f"## {index}. {_markdown_text(section.title)}",
                "",
                _markdown_block(section.body),
                "",
            )
        )
    lines.extend((_markdown_block(result.closing), "", "---", ""))
    lines.extend(("## 编辑摘要（发布前可选）", ""))
    lines.extend(f"- {_markdown_text(item)}" for item in result.key_points)
    lines.extend(
        (
            "",
            "## 编辑附录：视频证据（发布前可删除）",
            "",
            "> 以下时间码仅用于编辑回看原视频，不代表独立的外部事实核验。",
            "",
        )
    )
    for index, section in enumerate(result.sections, start=1):
        lines.extend((f"### {index}. {_markdown_text(section.title)}", ""))
        lines.extend(
            (
                f"- {_format_range(item.start_ms, item.end_ms)}："
                f"{_markdown_text(item.note)}"
            )
            for item in section.evidence
        )
        lines.append("")
    if result.limitations:
        lines.extend(("### 事实边界与待核验项", ""))
        lines.extend(f"- {_markdown_text(item)}" for item in result.limitations)
    return "\n".join(lines).rstrip() + "\n"


def format_report_time(milliseconds: int) -> str:
    return _format_time(milliseconds)


def format_report_range(start_ms: int, end_ms: int) -> str:
    return _format_range(start_ms, end_ms)


def format_report_size(size_bytes: int) -> str:
    return _format_size(size_bytes)


def report_labels(language: str) -> dict[str, str]:
    return _labels(language)
