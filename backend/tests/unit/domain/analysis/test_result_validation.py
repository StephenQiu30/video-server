from __future__ import annotations

from copy import deepcopy

import pytest
from app.domain.analysis import (
    AnalysisLimits,
    AnalysisMedia,
    AnalysisValidationCode,
    AnalysisValidationError,
    parse_analysis_result,
)


def media() -> AnalysisMedia:
    return AnalysisMedia(duration_ms=3_000, container="mp4", size_bytes=4_096)


def document() -> dict[str, object]:
    return {
        "language": "zh-CN",
        "title": "视觉分析",
        "summary": {
            "text": "三个连续分镜。",
            "evidence_shot_ids": ["shot-1", "shot-3"],
        },
        "shots": [
            {
                "id": "shot-1",
                "index": 1,
                "start_ms": 0,
                "end_ms": 1_000,
                "representative_frame_ms": 500,
                "description": "人物进入画面。",
                "transition_in": "none",
                "shot_size": "wide",
                "camera_motion": "static",
                "narrative_function": "建立故事空间。",
                "highlight_score": 3,
                "visual_tags": ["人物", "室内"],
            },
            {
                "id": "shot-2",
                "index": 2,
                "start_ms": 1_000,
                "end_ms": 2_000,
                "representative_frame_ms": 1_500,
                "description": "产品特写。",
                "transition_in": "cut",
                "shot_size": "close_up",
                "camera_motion": "zoom",
                "narrative_function": "突出核心产品信息。",
                "highlight_score": 5,
                "visual_tags": ["产品"],
            },
            {
                "id": "shot-3",
                "index": 3,
                "start_ms": 2_000,
                "end_ms": 3_000,
                "representative_frame_ms": 2_500,
                "description": "品牌标识收尾。",
                "transition_in": "dissolve",
                "shot_size": "medium",
                "camera_motion": "pan",
                "narrative_function": "完成品牌信息收束。",
                "highlight_score": 4,
                "visual_tags": ["标识"],
            },
        ],
        "highlights": [
            {
                "id": "highlight-1",
                "title": "产品亮相",
                "description": "产品在中心位置出现。",
                "score": 91,
                "reason": "视觉主体清晰且信息密度高。",
                "evidence_shot_ids": ["shot-2", "shot-3"],
            }
        ],
        "assets": [
            {
                "id": "asset-person",
                "type": "person",
                "label": "出镜人物",
                "description": "穿深色上衣的人物。",
                "evidence_shot_ids": ["shot-1"],
            },
            {
                "id": "asset-product",
                "type": "product",
                "label": "演示产品",
                "description": "画面中心的产品。",
                "evidence_shot_ids": ["shot-2", "shot-3"],
            },
        ],
        "production_advice": {
            "summary": "优先还原产品特写与品牌收尾镜头。",
            "priority_shot_ids": ["shot-2", "shot-3"],
            "recommended_extensions": ["镜头 Prompt", "产品资产"],
        },
    }


def parse(payload: object, *, limits: AnalysisLimits | None = None) -> object:
    return parse_analysis_result(
        payload,
        media(),
        expected_language="zh-CN",
        limits=limits,
    )


def test_valid_result_derives_counts_times_and_reverse_asset_index() -> None:
    result = parse(document())

    assert result.shot_count == 3
    assert result.media.duration_ms == 3_000
    assert result.highlights[0].start_ms == 1_000
    assert result.highlights[0].end_ms == 3_000
    assert result.assets[1].first_seen_ms == 1_000
    assert result.shots[0].asset_ids == ("asset-person",)
    assert result.shots[2].asset_ids == ("asset-product",)


@pytest.mark.parametrize(
    ("mutation", "code"),
    [
        (("shots", 1, "start_ms", 1_100), AnalysisValidationCode.INVALID_TIME_RANGE),
        (("shots", 2, "end_ms", 2_900), AnalysisValidationCode.INVALID_TIME_RANGE),
        (("shots", 1, "index", 3), AnalysisValidationCode.INVALID_TIME_RANGE),
        (("shots", 0, "transition_in", "cut"), AnalysisValidationCode.INVALID_SCHEMA),
        (("shots", 1, "camera_motion", "orbit"), AnalysisValidationCode.INVALID_SCHEMA),
        (("highlights", 0, "score", 101), AnalysisValidationCode.INVALID_SCHEMA),
        (("shots", 0, "highlight_score", 0), AnalysisValidationCode.INVALID_SCHEMA),
        (("assets", 0, "type", "identity"), AnalysisValidationCode.INVALID_SCHEMA),
    ],
)
def test_time_enum_and_score_contracts_are_strict(
    mutation: tuple[str, int, str, object], code: AnalysisValidationCode
) -> None:
    payload = document()
    collection, index, field, value = mutation
    payload[collection][index][field] = value

    with pytest.raises(AnalysisValidationError) as caught:
        parse(payload)
    assert caught.value.code is code


def test_unknown_empty_duplicate_and_orphan_evidence_are_rejected() -> None:
    extra = document()
    extra["confidence"] = 0.9
    empty = document()
    empty["summary"]["evidence_shot_ids"] = []
    duplicate = document()
    duplicate["assets"][0]["evidence_shot_ids"] = ["shot-1", "shot-1"]
    orphan = document()
    orphan["highlights"][0]["evidence_shot_ids"] = ["missing"]

    for payload in (extra, empty, duplicate, orphan):
        with pytest.raises(AnalysisValidationError):
            parse(payload)


def test_result_without_observable_shot_evidence_is_rejected() -> None:
    payload = document()
    for shot in payload["shots"]:
        shot["shot_size"] = "unknown"
        shot["camera_motion"] = "unknown"

    with pytest.raises(AnalysisValidationError) as caught:
        parse(payload)

    assert caught.value.code is AnalysisValidationCode.INVALID_EVIDENCE


def test_result_with_any_placeholder_visual_tags_is_rejected() -> None:
    payload = document()
    payload["shots"][1]["visual_tags"] = ["画面不可观察", "待重新抽帧分析"]

    with pytest.raises(AnalysisValidationError) as caught:
        parse(payload)

    assert caught.value.code is AnalysisValidationCode.INVALID_EVIDENCE


def test_language_nested_fields_ids_and_collection_limits_are_strict() -> None:
    wrong_language = document()
    wrong_language["language"] = "en-US"
    nested_extra = deepcopy(document())
    nested_extra["shots"][0]["confidence"] = 0.9
    duplicate_id = document()
    duplicate_id["shots"][1]["id"] = "shot-1"

    for payload in (wrong_language, nested_extra, duplicate_id):
        with pytest.raises(AnalysisValidationError):
            parse(payload)

    with pytest.raises(AnalysisValidationError) as limited:
        parse(document(), limits=AnalysisLimits(max_collection_items=2))
    assert limited.value.code is AnalysisValidationCode.LIMIT_EXCEEDED
