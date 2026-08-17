from __future__ import annotations

import html
import re

from app.domain.analysis import (
    ScreenplayAnalysisResult,
    ScreenplayEvidenceItem,
    ScreenplayRewriteResult,
)

_MARKDOWN_SPECIAL = re.compile(r"([\\`*_{}\[\]()#+.!|])")


def render_screenplay_report_markdown(
    result: ScreenplayAnalysisResult | ScreenplayRewriteResult,
) -> str:
    if isinstance(result, ScreenplayAnalysisResult):
        return _analysis_report(result)
    return _rewrite_report(result)


def _analysis_report(result: ScreenplayAnalysisResult) -> str:
    lines = [
        f"# {_inline(result.title)}",
        "",
        "> 剧本综合分析报告",
        "",
        "## 一、阅读摘要",
        "",
        f"- 输出语言：{_inline(result.language)}",
        f"- 逐场景分析：{len(result.scenes)} 个源场景，已按原文顺序覆盖",
        f"- 主要人物：{len(result.characters)} 个",
        "",
        "## 二、故事概览",
        "",
        "### 一句话梗概（Logline）",
        "",
        _inline(result.logline),
        "",
        "### 故事梗概（Synopsis）",
        "",
        _inline(result.synopsis),
        "",
        "## 三、结构与节奏",
        "",
    ]
    _evidence_items(lines, "幕结构", result.structure.acts)
    _evidence_items(lines, "关键转折", result.structure.turning_points)
    lines.extend(("### 节奏判断", "", _inline(result.structure.pacing_summary), ""))
    lines.extend(("## 四、人物分析", ""))
    if result.characters:
        for index, character in enumerate(result.characters, start=1):
            lines.extend(
                (
                    f"### {index}. {_inline(character.name)}",
                    "",
                    f"- 外部目标：{_inline(character.goal)}",
                    f"- 核心冲突：{_inline(character.conflict)}",
                    f"- 人物弧光：{_inline(character.arc)}",
                    f"- 证据场景：{_scene_refs(character.evidence_scene_ids)}",
                    "",
                )
            )
    else:
        lines.extend(("> 本次结果没有独立人物条目。", ""))
    lines.extend(("## 五、逐场景分析", ""))
    for index, scene in enumerate(result.scenes, start=1):
        lines.extend(
            (
                f"### 场景 {index}：{_inline(scene.source_scene_id)}",
                "",
                f"- 场景功能：{_inline(scene.purpose)}",
                f"- 冲突压力：{_inline(scene.conflict)}",
                f"- 场景转变：{_inline(scene.turn)}",
                f"- 节奏判断：{_inline(scene.pacing)}",
            )
        )
        lines.extend(f"- 发现：{_inline(item)}" for item in scene.findings)
        if not scene.findings:
            lines.append("- 发现：本场没有独立发现。")
        lines.extend((f"- 证据场景：{_inline(scene.source_scene_id)}", ""))
    lines.extend(("## 六、对白与写作", ""))
    _evidence_items(lines, "对白发现", result.dialogue_findings)
    lines.extend(("## 七、文本优势", ""))
    _evidence_items(lines, "优势", result.strengths)
    lines.extend(("## 八、优先修改建议", ""))
    _evidence_items(lines, "建议清单", result.priority_revisions)
    lines.extend(
        (
            "## 九、证据说明",
            "",
            "报告中的证据场景 ID 对应规范化剧本的源场景。"
            "逐场景分析已经由服务端校验为完整、唯一且保持原文顺序；"
            "全局结论只引用这些源场景。",
            "",
        )
    )
    return "\n".join(lines).rstrip() + "\n"


def _rewrite_report(result: ScreenplayRewriteResult) -> str:
    lines = [
        "# Screenplay rewrite",
        "",
        f"**Source language**: {_inline(result.source_language)}",
        "",
        f"**Target language**: {_inline(result.target_language)}",
        "",
        f"**Scenes**: {result.output_scene_count}",
        "",
        "## Glossary",
        "",
        "| Source | Target | Category |",
        "|---|---|---|",
    ]
    lines.extend(
        f"| {_inline(item.source)} | {_inline(item.target)} | "
        f"{_inline(item.category)} |"
        for item in result.glossary
    )
    lines.extend(("", "## Changes", ""))
    lines.extend(f"- {_inline(item)}" for item in result.change_summary)
    lines.extend(("", "## Rewritten screenplay", ""))
    current_scene = None
    for chunk in result.chunks:
        if chunk.source_scene_id != current_scene:
            current_scene = chunk.source_scene_id
            lines.extend((f"### {_inline(current_scene)}", ""))
        lines.extend((_body(chunk.rewritten_text), ""))
    return "\n".join(lines).rstrip() + "\n"


def _evidence_items(
    lines: list[str], title: str, items: tuple[ScreenplayEvidenceItem, ...]
) -> None:
    lines.extend((f"### {title}", ""))
    if not items:
        lines.extend(("> 本项没有独立发现。", ""))
        return
    for index, item in enumerate(items, start=1):
        lines.extend(
            (
                f"#### {index}. {_inline(item.title)}",
                "",
                _inline(item.description),
                "",
                f"证据场景：{_scene_refs(item.evidence_scene_ids)}",
                "",
            )
        )


def _scene_refs(values: tuple[str, ...]) -> str:
    return ", ".join(_inline(value) for value in values)


def _inline(value: str) -> str:
    escaped = html.escape(" ".join(value.split()), quote=False)
    return _MARKDOWN_SPECIAL.sub(r"\\\1", escaped)


def _body(value: str) -> str:
    return "  \n".join(
        _inline(line) if line.strip() else "" for line in value.splitlines()
    )
