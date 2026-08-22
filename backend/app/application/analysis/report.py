from __future__ import annotations

import html
import re

from app.application.analysis.screenplay_report import render_screenplay_report_markdown
from app.application.analysis.video_report_labels import video_report_labels as _labels
from app.domain.analysis import AnalysisResult, VideoAnalysisResult, VideoArticleResult

_MARKDOWN_SPECIAL = re.compile(r"([\\`*_{}\[\]()#+\-.!|])")


def render_analysis_report_markdown(result: AnalysisResult) -> str:
    if isinstance(result, VideoArticleResult):
        return _render_video_article_report_markdown(result)
    if not isinstance(result, VideoAnalysisResult):
        return render_screenplay_report_markdown(result)
    return _render_video_analysis_report_markdown(result)


def _render_video_article_report_markdown(result: VideoArticleResult) -> str:
    lines = [
        f"# {_markdown_text(result.title)} · 视频整理文章",
        "",
        "> 本文由视频分析整理生成；时间证据用于回看原视频，不代表独立的外部事实核验。",
        "",
        "## 导读",
        "",
        _markdown_block(result.lead),
        "",
        "## 正文",
        "",
    ]
    for index, section in enumerate(result.sections, start=1):
        lines.extend(
            (
                f"### {index}. {_markdown_text(section.title)}",
                "",
                _markdown_block(section.body),
                "",
                "**视频证据**",
                "",
            )
        )
        lines.extend(
            (
                f"- {_format_range(item.start_ms, item.end_ms)}："
                f"{_markdown_text(item.note)}"
            )
            for item in section.evidence
        )
        lines.append("")
    lines.extend(("## 核心观点", ""))
    lines.extend(f"- {_markdown_text(item)}" for item in result.key_points)
    lines.extend(("", "## 结语", "", _markdown_block(result.closing), ""))
    if result.limitations:
        lines.extend(("## 说明与局限", ""))
        lines.extend(f"- {_markdown_text(item)}" for item in result.limitations)
    return "\n".join(lines).rstrip() + "\n"


def _render_video_analysis_report_markdown(result: VideoAnalysisResult) -> str:
    labels = _labels(result.language)
    lines = [
        f"# {_markdown_text(result.title)} · {labels['report_title']}",
        "",
        labels["report_intro"],
        "",
        f"## {labels['basic_info']}",
        "",
        f"**{labels['duration']}**: {_format_time(result.media.duration_ms)}",
        "",
        f"**{labels['analysis_method']}**: {labels['cut_analysis']}",
        "",
        f"**{labels['shot_statistics']}**: {labels['cut_statistics']}",
        "",
        f"**{labels['director_summary']}**: {_markdown_text(result.summary.text)}",
        "",
        (
            f"| {labels['shot_number']} | {labels['timecode']} | "
            f"{labels['shot_duration']} | {labels['picture_content']} | "
            f"{labels['camera_language']} | {labels['narrative']} | "
            f"{labels['highlight_level']} |"
        ),
        "|---|---|---:|---|---|---|---|",
    ]
    for shot in result.shots:
        camera_language = " / ".join(
            (shot.shot_size, shot.camera_motion, shot.transition_in)
        )
        lines.append(
            f"| Shot {shot.index:03d} | {_format_range(shot.start_ms, shot.end_ms)} | "
            f"{_format_shot_duration(shot.start_ms, shot.end_ms)} | "
            f"{_markdown_text(shot.description)} | "
            f"{_markdown_text(camera_language)} | "
            f"{_markdown_text(shot.narrative_function)} | "
            f"{'★' * shot.highlight_score} |"
        )

    lines.extend(("", f"## {labels['highlights']}", ""))
    if not result.highlights:
        lines.extend((labels["no_highlights"], ""))
    for index, highlight in enumerate(result.highlights, start=1):
        lines.append(
            f"{index}. **{_markdown_text(highlight.title)}**："
            f"{_markdown_text(highlight.description)} "
            f"{_markdown_text(highlight.reason)}"
        )

    advice = result.production_advice
    shot_indexes = {shot.id: shot.index for shot in result.shots}
    priority = "、".join(
        f"Shot {shot_indexes[shot_id]:03d}" for shot_id in advice.priority_shot_ids
    )
    lines.extend(
        (
            "",
            f"## {labels['production_advice']}",
            "",
            _markdown_text(advice.summary),
            "",
            f"**{labels['priority_shots']}**: {priority}",
            "",
            f"**{labels['recommended_extensions']}**:",
            "",
        )
    )
    lines.extend(
        f"- {_markdown_text(extension)}" for extension in advice.recommended_extensions
    )

    lines.extend(("", f"## {labels['assets']}", ""))
    if not result.assets:
        lines.extend((labels["no_assets"], ""))
    for asset in result.assets:
        lines.extend(
            (
                f"### {_markdown_text(asset.label)}",
                "",
                f"- {labels['type']}: {_markdown_text(asset.type)}",
                f"- {labels['first_seen']}: {_format_time(asset.first_seen_ms)}",
                "",
                _markdown_text(asset.description),
                "",
            )
        )
    return "\n".join(lines).rstrip() + "\n"


def format_report_time(milliseconds: int) -> str:
    return _format_time(milliseconds)


def format_report_range(start_ms: int, end_ms: int) -> str:
    return _format_range(start_ms, end_ms)


def format_report_size(size_bytes: int) -> str:
    return _format_size(size_bytes)


def report_labels(language: str) -> dict[str, str]:
    return _labels(language)


def _markdown_text(value: str) -> str:
    normalized = " ".join(value.split())
    escaped_html = html.escape(normalized, quote=False)
    return _MARKDOWN_SPECIAL.sub(r"\\\1", escaped_html)


def _markdown_block(value: str) -> str:
    return "\n\n".join(
        _markdown_text(part) for part in value.splitlines() if part.strip()
    )


def _format_time(milliseconds: int) -> str:
    total_seconds, millis = divmod(milliseconds, 1_000)
    minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{millis:03d}"
    return f"{minutes:02d}:{seconds:02d}.{millis:03d}"


def _format_range(start_ms: int, end_ms: int) -> str:
    return f"{_format_time(start_ms)}–{_format_time(end_ms)}"


def _format_shot_duration(start_ms: int, end_ms: int) -> str:
    return f"{(end_ms - start_ms) / 1_000:.1f}s"


def _format_size(size_bytes: int) -> str:
    value = float(size_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1_024 or unit == "GB":
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1_024
    raise AssertionError("unreachable")
