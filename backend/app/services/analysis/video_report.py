from __future__ import annotations

from app.services.analysis.report_formatting import (
    format_time,
    markdown_block,
    markdown_text,
)
from app.services.analysis.rules.result_models import VideoAnalysisResult
from app.services.analysis.video_report_labels import video_report_labels
from app.services.analysis.video_report_sections import (
    append_advice,
    append_assets,
    append_highlights,
    append_shot_table,
    append_story_flow,
)


def render_video_analysis_report_markdown(result: VideoAnalysisResult) -> str:
    labels = video_report_labels(result.language)
    lines = [
        f"# {markdown_text(result.title)}",
        "",
        f"> {labels['deck']}",
        "",
        f"## {labels['takeaway']}",
        "",
        markdown_block(result.summary.text),
        "",
        _fact_line(result, labels),
        "",
    ]
    append_story_flow(lines, result, labels)
    append_shot_table(lines, result, labels)
    append_highlights(lines, result, labels)
    append_advice(lines, result, labels)
    append_assets(lines, result, labels)
    lines.extend((f"## {labels['method']}", "", labels["method_note"], ""))
    return "\n".join(lines).rstrip() + "\n"


def _fact_line(result: VideoAnalysisResult, labels: dict[str, str]) -> str:
    facts = (
        (labels["duration"], format_time(result.media.duration_ms)),
        (labels["segments"], str(result.shot_count)),
        (labels["scene_count"], str(len(result.scenes))),
        (labels["highlight_count"], str(len(result.highlights))),
    )
    return " · ".join(f"**{label}**{labels['colon']}{value}" for label, value in facts)
