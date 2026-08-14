from copy import deepcopy

import pytest
from app.domain.analysis import (
    AnalysisValidationError,
    parse_screenplay_glossary,
    parse_screenplay_rewrite_chunk,
)

_HASH = "a" * 64


def glossary_payload() -> dict[str, object]:
    return {
        "source_language": "mixed",
        "target_language": "en-US",
        "terms": [
            {"source": "林舟", "target": "Lin Zhou", "category": "character"},
            {
                "source": "剪辑室",
                "target": "editing room",
                "category": "location",
            },
        ],
        "style_rules": ["Use concise screenplay English."],
    }


def chunk_payload() -> dict[str, object]:
    return {
        "source_scene_id": "scene-1",
        "part_no": 1,
        "source_sha256": _HASH,
        "target_language": "en-US",
        "rewritten_text": "LIN ZHOU discovers that the ending footage is missing.\n",
        "change_summary": ["Localized the character name."],
    }


def test_glossary_parser_accepts_validated_terms_and_style_rules() -> None:
    result = parse_screenplay_glossary(
        glossary_payload(),
        expected_source_language="mixed",
        expected_target_language="en-US",
    )

    assert result.terms[0].target == "Lin Zhou"
    assert result.style_rules == ("Use concise screenplay English.",)


@pytest.mark.parametrize("mutation", ["language", "category", "duplicate", "extra"])
def test_glossary_parser_rejects_drift_and_ambiguous_terms(mutation: str) -> None:
    payload = glossary_payload()
    terms = payload["terms"]
    assert isinstance(terms, list) and isinstance(terms[0], dict)
    if mutation == "language":
        payload["target_language"] = "zh-CN"
    elif mutation == "category":
        terms[0]["category"] = "command"
    elif mutation == "duplicate":
        duplicate = deepcopy(terms[0])
        duplicate["source"] = "林舟"
        terms.append(duplicate)
    else:
        payload["unexpected"] = True

    with pytest.raises(AnalysisValidationError):
        parse_screenplay_glossary(
            payload,
            expected_source_language="mixed",
            expected_target_language="en-US",
        )


def test_rewrite_chunk_parser_binds_source_identity_and_target_language() -> None:
    result = parse_screenplay_rewrite_chunk(
        chunk_payload(),
        expected_scene_id="scene-1",
        expected_part_no=1,
        expected_source_sha256=_HASH,
        expected_target_language="en-US",
    )

    assert result.chunk.source_sha256 == _HASH
    assert result.chunk.rewritten_text.startswith("LIN ZHOU")
    assert result.chunk.rewritten_text.endswith("\n")


@pytest.mark.parametrize(
    "field", ["source_scene_id", "part_no", "source_sha256", "target_language"]
)
def test_rewrite_chunk_parser_rejects_identity_drift(field: str) -> None:
    payload = chunk_payload()
    payload[field] = 2 if field == "part_no" else "unexpected"

    with pytest.raises(AnalysisValidationError):
        parse_screenplay_rewrite_chunk(
            payload,
            expected_scene_id="scene-1",
            expected_part_no=1,
            expected_source_sha256=_HASH,
            expected_target_language="en-US",
        )
