from __future__ import annotations

from app.application.analysis.report_formatting import (
    format_range,
    format_shot_duration,
    format_time,
    markdown_block,
    markdown_text,
)
from app.domain.analysis import VideoAnalysisResult

_ZH_TERMS = {
    "extreme_wide": "大远景",
    "wide": "全景",
    "medium": "中景",
    "close_up": "特写",
    "extreme_close_up": "大特写",
    "static": "固定",
    "pan": "横摇",
    "tilt": "纵摇",
    "zoom": "变焦",
    "dolly": "推拉",
    "tracking": "跟拍",
    "handheld": "手持",
    "mixed": "混合",
    "unknown": "待确认",
    "cut": "硬切",
    "fade": "淡入淡出",
    "dissolve": "叠化",
    "wipe": "划像",
    "continuous": "连续节拍",
    "none": "起始",
    "person": "人物",
    "location": "场景空间",
    "object": "道具或物件",
    "product": "产品",
    "logo": "Logo",
    "on_screen_text": "画面文字",
}


def append_story_flow(
    lines: list[str], result: VideoAnalysisResult, labels: dict[str, str]
) -> None:
    lines.extend((f"## {labels['story_flow']}", "", labels["story_flow_intro"], ""))
    for scene in result.scenes:
        lines.extend(
            (
                f"### {scene.index:02d}｜{markdown_text(scene.title)}",
                "",
                (
                    f"> {format_range(scene.start_ms, scene.end_ms)} · "
                    f"{labels['location']}{labels['colon']}"
                    f"{markdown_text(scene.location)}"
                ),
                "",
                markdown_block(scene.description),
                "",
                f"**{labels['scene_role']}**{labels['colon']}"
                f"{markdown_text(scene.narrative_function)}",
                "",
                f"**{labels['visual_rules']}**",
                "",
            )
        )
        lines.extend(f"- {markdown_text(item)}" for item in scene.visual_rules)
        if scene.continuity_risks:
            lines.extend(("", f"**{labels['watch_out']}**", ""))
            lines.extend(f"- {markdown_text(item)}" for item in scene.continuity_risks)
        lines.append("")


def append_shot_table(
    lines: list[str], result: VideoAnalysisResult, labels: dict[str, str]
) -> None:
    lines.extend(
        (
            f"## {labels['shot_breakdown']}",
            "",
            labels["shot_breakdown_intro"],
            "",
            (
                f"| {labels['shot_number']} | {labels['timecode']} | "
                f"{labels['shot_duration']} | {labels['picture_content']} | "
                f"{labels['camera_language']} | {labels['narrative']} | "
                f"{labels['highlight_level']} |"
            ),
            "|---|---|---:|---|---|---|---|",
        )
    )
    for shot in result.shots:
        camera_language = " / ".join(
            _term(value, result.language)
            for value in (shot.shot_size, shot.camera_motion, shot.transition_in)
        )
        lines.append(
            f"| {_shot_ref(shot.index, labels)} | "
            f"{format_range(shot.start_ms, shot.end_ms)} | "
            f"{format_shot_duration(shot.start_ms, shot.end_ms)} | "
            f"{markdown_text(shot.description)} | {markdown_text(camera_language)} | "
            f"{markdown_text(shot.narrative_function)} | "
            f"{'★' * shot.highlight_score} |"
        )
    lines.append("")


def append_highlights(
    lines: list[str], result: VideoAnalysisResult, labels: dict[str, str]
) -> None:
    lines.extend((f"## {labels['highlights']}", ""))
    if not result.highlights:
        lines.extend((labels["no_highlights"], ""))
        return
    for index, highlight in enumerate(result.highlights, start=1):
        lines.extend(
            (
                f"### {index:02d}｜{markdown_text(highlight.title)}",
                "",
                markdown_block(highlight.description),
                "",
                f"**{labels['highlight_why']}**{labels['colon']}"
                f"{markdown_text(highlight.reason)}",
                "",
                (
                    f"**{labels['highlight_range']}**{labels['colon']}"
                    f"{format_range(highlight.start_ms, highlight.end_ms)} · "
                    f"{labels['relative_score']} {highlight.score}/100"
                ),
                "",
            )
        )


def append_advice(
    lines: list[str], result: VideoAnalysisResult, labels: dict[str, str]
) -> None:
    advice = result.production_advice
    shot_indexes = {shot.id: shot.index for shot in result.shots}
    priority = labels["list_separator"].join(
        _shot_ref(shot_indexes[shot_id], labels) for shot_id in advice.priority_shot_ids
    )
    lines.extend(
        (
            f"## {labels['production_advice']}",
            "",
            markdown_block(advice.summary),
            "",
            f"**{labels['priority_shots']}**{labels['colon']}{priority}",
            "",
        )
    )
    lines.extend(
        f"{index}. {markdown_text(item)}"
        for index, item in enumerate(advice.recommended_extensions, start=1)
    )
    lines.append("")


def append_assets(
    lines: list[str], result: VideoAnalysisResult, labels: dict[str, str]
) -> None:
    lines.extend((f"## {labels['assets']}", ""))
    if not result.assets:
        lines.extend((labels["no_assets"], ""))
        return
    for asset in result.assets:
        lines.extend(
            (
                f"### {markdown_text(asset.label)}",
                "",
                (
                    f"**{labels['asset_type']}**{labels['colon']}"
                    f"{_term(asset.type, result.language)} · "
                    f"**{labels['first_seen']}**{labels['colon']}"
                    f"{format_time(asset.first_seen_ms)}"
                ),
                "",
                markdown_block(asset.description),
                "",
            )
        )


def _shot_ref(index: int, labels: dict[str, str]) -> str:
    return f"{labels['shot_ref']} {index:03d}"


def _term(value: str, language: str) -> str:
    if language.lower().startswith("zh"):
        return _ZH_TERMS.get(value, value.replace("_", " "))
    return value.replace("_", " ")
