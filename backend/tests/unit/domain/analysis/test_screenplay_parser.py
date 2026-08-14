from __future__ import annotations

import json
from dataclasses import asdict
from enum import Enum

import pytest
from app.domain.analysis import (
    AnalysisValidationError,
    parse_screenplay_analysis_result,
)
from tests.unit.domain.analysis.screenplay_factories import screenplay_analysis_result


def payload() -> dict[str, object]:
    document = json.loads(
        json.dumps(
            asdict(screenplay_analysis_result()),
            ensure_ascii=False,
            default=lambda value: value.value if isinstance(value, Enum) else value,
        )
    )
    document.pop("kind")
    document["priority_revisions"] = [
        {
            "id": "revision-1",
            "title": "强化阻力",
            "description": "让危机更早影响人物选择。",
            "evidence_scene_ids": ["scene-1"],
        }
    ]
    return document


def test_screenplay_parser_accepts_exact_source_scene_coverage() -> None:
    result = parse_screenplay_analysis_result(
        payload(), expected_language="zh-CN", source_scene_ids=("scene-1",)
    )

    assert result.title == "剧本分析"
    assert result.scenes[0].source_scene_id == "scene-1"
    assert result.characters[0].evidence_scene_ids == ("scene-1",)


def test_screenplay_parser_rejects_reordered_source_scenes() -> None:
    value = payload()
    scenes = value["scenes"]
    assert isinstance(scenes, list) and isinstance(scenes[0], dict)
    second = dict(scenes[0])
    second.update(id="analysis-scene-2", source_scene_id="scene-2")
    scenes.append(second)
    scenes.reverse()

    with pytest.raises(AnalysisValidationError):
        parse_screenplay_analysis_result(
            value,
            expected_language="zh-CN",
            source_scene_ids=("scene-1", "scene-2"),
        )


@pytest.mark.parametrize("mutation", ["language", "extra", "coverage"])
def test_screenplay_parser_rejects_language_shape_and_scene_drift(
    mutation: str,
) -> None:
    value = payload()
    if mutation == "language":
        value["language"] = "en-US"
    elif mutation == "extra":
        value["unexpected"] = "value"
    else:
        scenes = value["scenes"]
        assert isinstance(scenes, list) and isinstance(scenes[0], dict)
        scenes[0]["source_scene_id"] = "invented-scene"

    with pytest.raises(AnalysisValidationError):
        parse_screenplay_analysis_result(
            value, expected_language="zh-CN", source_scene_ids=("scene-1",)
        )
