import hashlib
from dataclasses import replace

import pytest
from app.application.analysis import (
    AnalysisApplicationError,
    AnalysisApplicationErrorCode,
    AnalysisStoredReportFile,
    render_analysis_report_markdown,
)
from app.application.analysis.export_report import _read_verified
from app.application.analysis.screenplay_report import render_screenplay_report_markdown
from app.domain.analysis import (
    AnalysisMedia,
    Highlight,
    VisualAsset,
    parse_analysis_result,
    parse_video_article_result,
)
from tests.unit.domain.analysis.screenplay_factories import screenplay_analysis_result
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
    assert "逐分镜（Cut + 连续节拍）分析" in markdown
    assert "不按固定秒数切片" in markdown
    assert "| 镜头编号 | 时间码 | 时长 | 画面内容 |" in markdown
    assert "| Shot 001 | 00:00.000–00:02.000 | 2.0s |" in markdown
    assert "## 二、场景提炼" in markdown
    assert "### 场景 1: 开场建立" in markdown
    assert "## 三、高光镜头分析" in markdown
    assert "## 四、AI 制作建议" in markdown
    assert "## 五、视觉资产目录" in markdown
    assert "&lt;script&gt;alert\\(1\\)&lt;/script&gt;" in markdown
    assert "\\*\\*重点\\*\\*" in markdown
    assert markdown.endswith("\n")


def test_screenplay_report_uses_coverage_sections_and_explains_evidence() -> None:
    result = replace(
        screenplay_analysis_result(),
        title="剧本 [分析] <草稿>",
        synopsis="开端\n\n升级与选择。",
    )

    markdown = render_screenplay_report_markdown(result)

    assert markdown.startswith("# 剧本 \\[分析\\] &lt;草稿&gt;")
    assert "## 一、阅读摘要" in markdown
    assert "- 逐场景分析：1 个源场景，已按原文顺序覆盖" in markdown
    assert "## 五、逐场景分析" in markdown
    assert "### 场景 1：scene-1" in markdown
    assert "## 八、优先修改建议" in markdown
    assert "> 本项没有独立发现。" in markdown
    assert "## 九、证据说明" in markdown
    assert "逐场景分析已经由服务端校验为完整、唯一且保持原文顺序" in markdown
    assert markdown.endswith("\n")


def test_video_article_report_keeps_topic_structure_and_evidence() -> None:
    result = parse_video_article_result(
        {
            "language": "zh-CN",
            "title": "问题如何变成方法",
            "lead": "视频用一个具体问题引出一套可复用的方法。",
            "sections": [
                {
                    "id": "section-1",
                    "title": "从问题开始",
                    "body": "先把问题说清楚，再决定下一步。",
                    "evidence": [
                        {"start_ms": 0, "end_ms": 2_000, "note": "开场问题场景。"}
                    ],
                }
            ],
            "key_points": ["先定义问题，再选择方法。"],
            "closing": "方法的价值在于可以被复用。",
            "limitations": [],
        },
        AnalysisMedia(duration_ms=2_000, container="mp4", size_bytes=1_024),
        expected_language="zh-CN",
    )

    markdown = render_analysis_report_markdown(result)

    assert markdown.startswith("# 问题如何变成方法\n\n视频用一个具体问题")
    assert "## 1. 从问题开始" in markdown
    assert "00:00.000–00:02.000" in markdown
    assert "## 编辑摘要（发布前可选）" in markdown
    assert "## 编辑附录：视频证据（发布前可删除）" in markdown
    assert markdown.index("方法的价值在于可以被复用。") < markdown.index(
        "00:00.000–00:02.000"
    )


class ObjectReader:
    def __init__(self, content: bytes | Exception) -> None:
        self.content = content

    async def read(self, object_key: str) -> bytes:
        if isinstance(self.content, Exception):
            raise self.content
        return self.content


@pytest.mark.asyncio
async def test_stored_report_download_verifies_size_and_sha256() -> None:
    content = b"# verified report\n"
    stored = AnalysisStoredReportFile(
        object_key="private/report.md",
        media_type="text/markdown; charset=utf-8",
        size_bytes=len(content),
        sha256=hashlib.sha256(content).hexdigest(),
    )

    assert await _read_verified(ObjectReader(content), stored) == content
    for reader in (ObjectReader(b"corrupt"), ObjectReader(FileNotFoundError())):
        with pytest.raises(AnalysisApplicationError) as caught:
            await _read_verified(reader, stored)
        assert caught.value.code is AnalysisApplicationErrorCode.REPORT_UNAVAILABLE
