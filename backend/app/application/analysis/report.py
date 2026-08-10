from __future__ import annotations

import html
import re

from app.domain.analysis import AnalysisResult

_MARKDOWN_SPECIAL = re.compile(r"([\\`*_{}\[\]()#+\-.!|])")


def render_analysis_report_markdown(result: AnalysisResult) -> str:
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


def _labels(language: str) -> dict[str, str]:
    if language.lower().startswith("zh"):
        return {
            "report_title": "逐镜头导演拉片分析报告",
            "report_intro": (
                "本报告按照影视导演拉片方式进行整理，采用实际剪辑切点（Cut）进行"
                "镜头拆解，重点分析镜头时长、画面信息、景别、摄影语言、叙事作用、"
                "情绪价值及高光镜头。"
            ),
            "basic_info": "一、基础信息",
            "analysis_method": "分析方式",
            "cut_analysis": "逐镜头（Cut 级）分析",
            "shot_statistics": "镜头统计",
            "cut_statistics": "根据画面切换进行拆分，不按照剧情段落合并。",
            "director_summary": "导演综述",
            "shot_number": "镜头编号",
            "timecode": "时间码",
            "shot_duration": "时长",
            "picture_content": "画面内容",
            "camera_language": "景别 / 摄影语言",
            "narrative": "叙事作用",
            "highlight_level": "高光等级",
            "production_advice": "三、AI 制作建议",
            "priority_shots": "重点还原镜头",
            "recommended_extensions": "建议扩展",
            "subtitle": "AI 视频视觉分析报告",
            "overview": "报告概览",
            "language": "输出语言",
            "duration": "视频时长",
            "format": "文件格式",
            "size": "文件大小",
            "shots": "分镜数量",
            "summary": "视觉摘要",
            "shot_list": "分镜分析",
            "shot_size": "景别",
            "camera": "镜头运动",
            "transition": "转场",
            "tags": "视觉标签",
            "none": "无",
            "highlights": "二、高光镜头分析",
            "no_highlights": "未识别出独立视觉高光。",
            "time": "时间范围",
            "reason": "入选理由",
            "assets": "四、视觉资产目录",
            "no_assets": "未识别出可复用的视觉资产。",
            "type": "类型",
            "label": "名称",
            "first_seen": "首次出现",
        }
    return {
        "report_title": "Shot-by-shot director breakdown",
        "report_intro": (
            "This report uses actual editing cuts to examine shot duration, visual "
            "content, framing, camera language, narrative function, emotional value, "
            "and highlight shots."
        ),
        "basic_info": "1. Basic information",
        "analysis_method": "Analysis method",
        "cut_analysis": "Shot-by-shot cut analysis",
        "shot_statistics": "Shot segmentation",
        "cut_statistics": "Split on visible cuts rather than merged story beats.",
        "director_summary": "Director summary",
        "shot_number": "Shot",
        "timecode": "Timecode",
        "shot_duration": "Duration",
        "picture_content": "Visual content",
        "camera_language": "Framing / camera language",
        "narrative": "Narrative function",
        "highlight_level": "Highlight level",
        "production_advice": "3. AI production advice",
        "priority_shots": "Priority shots",
        "recommended_extensions": "Recommended extensions",
        "subtitle": "AI visual analysis report",
        "overview": "Report overview",
        "language": "Output language",
        "duration": "Duration",
        "format": "Format",
        "size": "File size",
        "shots": "Shot count",
        "summary": "Visual summary",
        "shot_list": "Shot analysis",
        "shot_size": "Shot size",
        "camera": "Camera motion",
        "transition": "Transition",
        "tags": "Visual tags",
        "none": "None",
        "highlights": "2. Highlight shot analysis",
        "no_highlights": "No distinct visual highlights were identified.",
        "time": "Time range",
        "reason": "Selection reason",
        "assets": "4. Visual asset catalog",
        "no_assets": "No reusable visual assets were identified.",
        "type": "Type",
        "label": "Label",
        "first_seen": "First seen",
    }
