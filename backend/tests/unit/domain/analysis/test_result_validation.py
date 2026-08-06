from __future__ import annotations

from copy import deepcopy

import pytest
from app.domain.analysis import (
    AnalysisLimits,
    AnalysisValidationCode,
    AnalysisValidationError,
    Transcript,
    TranscriptSegment,
    parse_analysis_result,
)


def transcript() -> Transcript:
    return Transcript(
        (
            TranscriptSegment("s1", 0, 1_000, "zh-CN", "第一段。"),
            TranscriptSegment("s2", 1_000, 2_000, "en-US", "Second segment."),
            TranscriptSegment("s3", 2_000, 3_000, "zh-CN", "第三段。"),
        )
    )


def document() -> dict[str, object]:
    return {
        "schema_version": "analysis.v1",
        "language": "zh-CN",
        "title": "双语视频分析",
        "summary": {"text": "主要摘要", "evidence_segment_ids": ["s1", "s2"]},
        "key_points": [
            {"text": "关键观点", "evidence_segment_ids": ["s1"]},
        ],
        "action_items": [
            {"text": "后续行动", "evidence_segment_ids": ["s3"]},
        ],
        "chapters": [
            {
                "title": "开场",
                "start_ms": 0,
                "end_ms": 2_000,
                "summary": "开场摘要",
                "evidence_segment_ids": ["s1", "s2"],
            },
            {
                "title": "结尾",
                "start_ms": 2_000,
                "end_ms": 3_000,
                "summary": "结尾摘要",
                "evidence_segment_ids": ["s3"],
            },
        ],
        "mind_map": {
            "id": "root",
            "title": "主题",
            "summary": "根节点",
            "start_ms": 0,
            "evidence_segment_ids": ["s1", "s2"],
            "children": [
                {
                    "id": "child",
                    "title": "子主题",
                    "summary": None,
                    "start_ms": 2_000,
                    "evidence_segment_ids": ["s3"],
                    "children": [],
                }
            ],
        },
    }


def parse(payload: object) -> object:
    return parse_analysis_result(
        payload,
        transcript(),
        expected_schema_version="analysis.v1",
        expected_language="zh-CN",
    )


def test_valid_result_maps_every_conclusion_to_real_evidence() -> None:
    result = parse(document())

    assert result.title == "双语视频分析"
    assert result.summary.evidence_segment_ids == ("s1", "s2")
    assert result.action_items[0].evidence_segment_ids == ("s3",)
    assert result.mind_map.children[0].start_ms == 2_000


@pytest.mark.parametrize("section", ["summary", "key_points", "action_items"])
def test_orphan_evidence_is_rejected_for_conclusions(section: str) -> None:
    payload = document()
    target = payload[section]
    if isinstance(target, list):
        target[0]["evidence_segment_ids"] = ["missing"]
    else:
        target["evidence_segment_ids"] = ["missing"]

    with pytest.raises(AnalysisValidationError) as caught:
        parse(payload)
    assert caught.value.code is AnalysisValidationCode.INVALID_EVIDENCE


def test_chapter_and_mind_map_evidence_must_match_time_ranges() -> None:
    chapter = document()
    chapter["chapters"][0]["evidence_segment_ids"] = ["s3"]
    with pytest.raises(AnalysisValidationError) as chapter_error:
        parse(chapter)
    assert chapter_error.value.code is AnalysisValidationCode.INVALID_TIME_RANGE

    node = document()
    node["mind_map"]["children"][0]["start_ms"] = 1_000
    with pytest.raises(AnalysisValidationError) as node_error:
        parse(node)
    assert node_error.value.code is AnalysisValidationCode.INVALID_TIME_RANGE


def test_empty_duplicate_and_orphan_evidence_are_rejected() -> None:
    empty = document()
    empty["summary"]["evidence_segment_ids"] = []
    duplicate = document()
    duplicate["summary"]["evidence_segment_ids"] = ["s1", "s1"]
    orphan = document()
    orphan["mind_map"]["evidence_segment_ids"] = ["missing"]

    for payload in (empty, duplicate, orphan):
        with pytest.raises(AnalysisValidationError):
            parse(payload)


def test_extra_fields_duplicate_nodes_cycles_depth_and_size_are_rejected() -> None:
    extra = document()
    extra["unexpected"] = "model commentary"
    duplicate = document()
    duplicate["mind_map"]["children"][0]["id"] = "root"
    cyclic = document()
    root = cyclic["mind_map"]
    root["children"] = [root]

    for payload in (extra, duplicate, cyclic):
        with pytest.raises(AnalysisValidationError):
            parse(payload)

    limited = document()
    with pytest.raises(AnalysisValidationError) as too_deep:
        parse_analysis_result(
            limited,
            transcript(),
            expected_schema_version="analysis.v1",
            expected_language="zh-CN",
            limits=AnalysisLimits(max_mind_map_depth=1, max_mind_map_nodes=20),
        )
    assert too_deep.value.code is AnalysisValidationCode.LIMIT_EXCEEDED

    with pytest.raises(AnalysisValidationError) as too_many:
        parse_analysis_result(
            limited,
            transcript(),
            expected_schema_version="analysis.v1",
            expected_language="zh-CN",
            limits=AnalysisLimits(max_mind_map_depth=8, max_mind_map_nodes=1),
        )
    assert too_many.value.code is AnalysisValidationCode.LIMIT_EXCEEDED


def test_schema_language_chapter_order_and_nested_extra_fields_are_strict() -> None:
    wrong_schema = document()
    wrong_schema["schema_version"] = "analysis.v2"
    wrong_language = document()
    wrong_language["language"] = "en-US"
    reversed_chapters = document()
    reversed_chapters["chapters"] = list(reversed(reversed_chapters["chapters"]))
    nested_extra = deepcopy(document())
    nested_extra["summary"]["confidence"] = 0.9

    for payload in (
        wrong_schema,
        wrong_language,
        reversed_chapters,
        nested_extra,
    ):
        with pytest.raises(AnalysisValidationError):
            parse(payload)
