from __future__ import annotations

import html
import re

from app.domain.analysis import (
    ScreenplayAnalysisResult,
    ScreenplayEvidenceItem,
    ScreenplayRewriteResult,
)

_MARKDOWN_SPECIAL = re.compile(r"([\\`*_{}\[\]()#+\-.!|])")


def render_screenplay_report_markdown(
    result: ScreenplayAnalysisResult | ScreenplayRewriteResult,
) -> str:
    if isinstance(result, ScreenplayAnalysisResult):
        return _analysis_report(result)
    return _rewrite_report(result)


def _analysis_report(result: ScreenplayAnalysisResult) -> str:
    lines = [
        f"# {_text(result.title)}",
        "",
        f"**Language**: {_text(result.language)}",
        "",
        "## Logline",
        "",
        _text(result.logline),
        "",
        "## Synopsis",
        "",
        _text(result.synopsis),
        "",
        "## Structure",
        "",
        _text(result.structure.pacing_summary),
        "",
    ]
    _evidence_section(lines, "Acts", result.structure.acts)
    _evidence_section(lines, "Turning points", result.structure.turning_points)
    lines.extend(("## Characters", ""))
    for character in result.characters:
        lines.extend(
            (
                f"### {_text(character.name)}",
                "",
                f"- Goal: {_text(character.goal)}",
                f"- Conflict: {_text(character.conflict)}",
                f"- Arc: {_text(character.arc)}",
                f"- Evidence: {_scene_refs(character.evidence_scene_ids)}",
                "",
            )
        )
    lines.extend(("## Scene analysis", ""))
    for scene in result.scenes:
        lines.extend(
            (
                f"### {_text(scene.source_scene_id)}",
                "",
                f"- Purpose: {_text(scene.purpose)}",
                f"- Conflict: {_text(scene.conflict)}",
                f"- Turn: {_text(scene.turn)}",
                f"- Pacing: {_text(scene.pacing)}",
            )
        )
        lines.extend(f"- {_text(item)}" for item in scene.findings)
        lines.append("")
    _evidence_section(lines, "Dialogue findings", result.dialogue_findings)
    _evidence_section(lines, "Strengths", result.strengths)
    _evidence_section(lines, "Priority revisions", result.priority_revisions)
    return "\n".join(lines).rstrip() + "\n"


def _rewrite_report(result: ScreenplayRewriteResult) -> str:
    lines = [
        "# Screenplay rewrite",
        "",
        f"**Source language**: {_text(result.source_language)}",
        "",
        f"**Target language**: {_text(result.target_language)}",
        "",
        f"**Scenes**: {result.output_scene_count}",
        "",
        "## Glossary",
        "",
        "| Source | Target | Category |",
        "|---|---|---|",
    ]
    lines.extend(
        f"| {_text(item.source)} | {_text(item.target)} | {_text(item.category)} |"
        for item in result.glossary
    )
    lines.extend(("", "## Changes", ""))
    lines.extend(f"- {_text(item)}" for item in result.change_summary)
    lines.extend(("", "## Rewritten screenplay", ""))
    current_scene = None
    for chunk in result.chunks:
        if chunk.source_scene_id != current_scene:
            current_scene = chunk.source_scene_id
            lines.extend((f"### {_text(current_scene)}", ""))
        lines.extend((_body(chunk.rewritten_text), ""))
    return "\n".join(lines).rstrip() + "\n"


def _evidence_section(
    lines: list[str], title: str, items: tuple[ScreenplayEvidenceItem, ...]
) -> None:
    lines.extend((f"## {title}", ""))
    for item in items:
        lines.extend(
            (
                f"### {_text(item.title)}",
                "",
                _text(item.description),
                "",
                f"Evidence: {_scene_refs(item.evidence_scene_ids)}",
                "",
            )
        )


def _scene_refs(values: tuple[str, ...]) -> str:
    return ", ".join(_text(value) for value in values)


def _text(value: str) -> str:
    escaped = html.escape(" ".join(value.split()), quote=False)
    return _MARKDOWN_SPECIAL.sub(r"\\\1", escaped)


def _body(value: str) -> str:
    return "  \n".join(
        _text(line) if line.strip() else "" for line in value.splitlines()
    )
