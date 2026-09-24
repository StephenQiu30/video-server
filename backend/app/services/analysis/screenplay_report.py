from __future__ import annotations

import html
import re

from app.services.analysis.rules.screenplay_result_items import ScreenplayFinding
from app.services.analysis.rules.screenplay_results import (
    ScreenplayAnalysisResult,
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
        "> 剧本故事审稿报告",
        "",
        "## 一、审稿重点",
        "",
        f"- 输出语言：{_inline(result.language)}",
        f"- 逐场景分析：{len(result.scenes)} 个源场景，已按原文顺序覆盖",
        f"- 主要人物：{len(result.characters)} 个",
        "",
    ]
    _findings(
        lines,
        "优先修改",
        result.priority_revisions,
        empty_message="本次审稿没有提出有充分文本依据的优先修改项。",
    )
    _findings(
        lines,
        "值得保留",
        result.strengths,
        empty_message="本次审稿没有单列文本优势。",
    )
    lines.extend(
        (
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
        )
    )
    _findings(lines, "幕结构", result.structure.acts)
    _findings(lines, "关键转折", result.structure.turning_points)
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
                    "",
                )
            )
    else:
        lines.extend(("> 本次结果没有独立人物条目。", ""))
    lines.extend(("## 五、对白与写作", ""))
    _findings(lines, "对白发现", result.dialogue_findings)
    lines.extend(("## 六、逐场景附录", ""))
    for index, scene in enumerate(result.scenes, start=1):
        lines.extend(
            (
                f"### 场景 {index}",
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
        lines.append("")
    lines.extend(
        (
            "## 七、阅读说明",
            "",
            "场景序号按上传剧本的规范化文本顺序排列。"
            "服务端校验了逐场景覆盖与顺序；分析判断仍需对照原文核查。",
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


def _findings(
    lines: list[str],
    title: str,
    items: tuple[ScreenplayFinding, ...],
    *,
    empty_message: str = "本项没有独立发现。",
) -> None:
    lines.extend((f"### {title}", ""))
    if not items:
        lines.extend((f"> {empty_message}", ""))
        return
    for index, item in enumerate(items, start=1):
        lines.append(
            f"{index}. **{_inline(item.title)}** — {_inline(item.description)}"
        )
    lines.append("")


def _inline(value: str) -> str:
    escaped = html.escape(" ".join(value.split()), quote=False)
    return _MARKDOWN_SPECIAL.sub(r"\\\1", escaped)


def _body(value: str) -> str:
    return "  \n".join(
        _inline(line) if line.strip() else "" for line in value.splitlines()
    )
