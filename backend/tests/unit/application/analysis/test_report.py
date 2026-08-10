from dataclasses import replace

from app.application.analysis import render_analysis_report_markdown
from app.domain.analysis import (
    AnalysisMedia,
    Highlight,
    VisualAsset,
    parse_analysis_result,
)
from tests.unit.workers.analysis.fixtures import valid_mapping


def report_result():
    payload = valid_mapping()
    payload["title"] = "产品 [演示](https://invalid.example)"
    payload["summary"] = {
        "text": "总结 <script>alert(1)</script> 与 **重点**。",
        "evidence_shot_ids": ["shot-a"],
    }
    result = parse_analysis_result(
        payload,
        AnalysisMedia(duration_ms=2_000, container="mp4", size_bytes=1_024),
        expected_language="zh-CN",
    )
    return replace(
        result,
        highlights=(
            Highlight(
                id="highlight-a",
                title="关键切换",
                description="展示主要界面。",
                score=92,
                reason="信息密度高。",
                start_ms=0,
                end_ms=2_000,
                evidence_shot_ids=("shot-a",),
            ),
        ),
        assets=(
            VisualAsset(
                id="asset-a",
                type="product",
                label="演示产品",
                description="画面中的产品界面。",
                first_seen_ms=0,
                evidence_shot_ids=("shot-a",),
            ),
        ),
    )


def test_markdown_report_is_complete_and_escapes_model_text() -> None:
    markdown = render_analysis_report_markdown(report_result())

    assert markdown.startswith("# 产品 \\[演示\\]\\(https://invalid\\.example\\)")
    assert "## 一、基础信息" in markdown
    assert "| 镜头编号 | 时间码 | 时长 | 画面内容 |" in markdown
    assert "| Shot 001 | 00:00.000–00:02.000 | 2.0s |" in markdown
    assert "## 二、高光镜头分析" in markdown
    assert "## 三、AI 制作建议" in markdown
    assert "## 四、视觉资产目录" in markdown
    assert "&lt;script&gt;alert\\(1\\)&lt;/script&gt;" in markdown
    assert "\\*\\*重点\\*\\*" in markdown
    assert markdown.endswith("\n")
