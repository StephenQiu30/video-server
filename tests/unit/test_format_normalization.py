from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from video_server.source.formats import normalize_formats

DATASET_PATH = (
    Path(__file__).parents[2] / "docs" / "acceptance" / "fixtures" / "DS-P1-FORMAT-8.json"
)
DATASET: dict[str, Any] = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
CASES: list[dict[str, Any]] = DATASET["cases"]
ORACLE_ONLY_FIELDS = {"components", "fingerprint_sha256"}


def _public_oracle(expected: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in expected.items() if key not in ORACLE_ONLY_FIELDS}


def _fingerprint_oracle(expected: dict[str, Any]) -> str:
    component_ids = expected["components"]
    fingerprint_object = {
        "audio_codec": expected["audio_codec"],
        "audio_format_id": component_ids[1] if expected["requires_merge"] else "",
        "container": expected["container"],
        "dynamic_range": expected["dynamic_range"],
        "estimated_bytes": expected["estimated_bytes"],
        "fps": expected["fps"],
        "has_audio": expected["has_audio"],
        "has_video": expected["has_video"],
        "height": expected["height"],
        "requires_merge": expected["requires_merge"],
        "size_is_estimate": expected["size_is_estimate"],
        "video_codec": expected["video_codec"],
        "video_format_id": component_ids[0],
        "width": expected["width"],
    }
    canonical_bytes = json.dumps(
        fingerprint_object,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    return hashlib.sha256(canonical_bytes).hexdigest()


def _observable(normalized: list[Any]) -> list[tuple[dict[str, Any], tuple[str, ...], str]]:
    return [
        (
            item.to_public_dict(),
            tuple(item.component_ids),
            item.fingerprint_sha256,
        )
        for item in normalized
    ]


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_normalize_formats_matches_frozen_manifest(case: dict[str, Any]) -> None:
    normalized = normalize_formats(case["input_formats"], case["locale"])
    expected_formats = case["expected_formats"]

    assert [item.to_public_dict() for item in normalized] == [
        _public_oracle(expected) for expected in expected_formats
    ]
    assert [tuple(item.component_ids) for item in normalized] == [
        tuple(expected["components"]) for expected in expected_formats
    ]
    assert [item.fingerprint_sha256 for item in normalized] == [
        expected.get("fingerprint_sha256", _fingerprint_oracle(expected))
        for expected in expected_formats
    ]


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_normalize_formats_is_deterministic_and_input_order_independent(
    case: dict[str, Any],
) -> None:
    original_input = copy.deepcopy(case["input_formats"])

    first = normalize_formats(case["input_formats"], case["locale"])
    second = normalize_formats(list(reversed(case["input_formats"])), case["locale"])

    assert _observable(first) == _observable(second)
    assert case["input_formats"] == original_input


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_normalize_formats_marks_only_the_first_candidate_recommended(
    case: dict[str, Any],
) -> None:
    public_formats = [
        item.to_public_dict() for item in normalize_formats(case["input_formats"], case["locale"])
    ]

    if not public_formats:
        assert case["expected_formats"] == []
        return

    assert [item["recommended"] for item in public_formats] == [True] + [False] * (
        len(public_formats) - 1
    )


def test_pure_normalizer_does_not_allocate_or_expose_snapshot_format_keys() -> None:
    case = next(case for case in CASES if case["id"] == "FORMAT-MULTI-SORT")

    first = normalize_formats(case["input_formats"], case["locale"])
    second = normalize_formats(case["input_formats"], case["locale"])

    assert _observable(first) == _observable(second)
    for item in [*first, *second]:
        public = item.to_public_dict()
        assert not hasattr(item, "format_key")
        assert "format_key" not in public
        assert "components" not in public
        assert "component_ids" not in public
        assert "fingerprint_sha256" not in public
