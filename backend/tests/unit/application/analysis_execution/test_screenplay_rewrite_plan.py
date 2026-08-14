import hashlib

import pytest
from app.application.analysis_execution import (
    AnalysisArtifactError,
    ScreenplaySceneSource,
    plan_screenplay_rewrite,
)


def scenes(text: str, split: int) -> tuple[ScreenplaySceneSource, ...]:
    return (
        ScreenplaySceneSource("scene-0001-aaaaaaaaaaaa", split, text.index("TWO")),
        ScreenplaySceneSource("scene-0002-bbbbbbbbbbbb", text.index("TWO"), len(text)),
    )


def test_rewrite_plan_preserves_preamble_and_exact_scene_order() -> None:
    text = "Title: Demo\n\nONE\nAction.\n\nTWO\nDialogue.\n"

    chunks = plan_screenplay_rewrite(
        text, scenes(text, text.index("ONE")), max_chunk_characters=100, max_chunks=10
    )

    assert [chunk.source_scene_id for chunk in chunks] == [
        "scene-0001-aaaaaaaaaaaa",
        "scene-0002-bbbbbbbbbbbb",
    ]
    assert "".join(chunk.text for chunk in chunks) == text
    assert chunks[0].text.startswith("Title: Demo")


def test_rewrite_plan_splits_scene_on_paragraphs_with_stable_hashes() -> None:
    text = "ONE\n12345678\n\nabcdefgh\n\nijklmnop\n"
    source = (ScreenplaySceneSource("scene-0001-aaaaaaaaaaaa", 0, len(text)),)

    chunks = plan_screenplay_rewrite(
        text, source, max_chunk_characters=18, max_chunks=10
    )

    assert len(chunks) == 3
    assert [chunk.part_no for chunk in chunks] == [1, 2, 3]
    assert all(len(chunk.text) <= 18 for chunk in chunks)
    assert "".join(chunk.text for chunk in chunks) == text
    assert all(
        chunk.source_sha256 == hashlib.sha256(chunk.text.encode()).hexdigest()
        for chunk in chunks
    )


def test_rewrite_plan_hard_splits_a_single_oversized_line() -> None:
    text = "ONE\n" + "字" * 25 + "\n"
    source = (ScreenplaySceneSource("scene-0001-aaaaaaaaaaaa", 0, len(text)),)

    chunks = plan_screenplay_rewrite(
        text, source, max_chunk_characters=10, max_chunks=10
    )

    assert all(len(chunk.text) <= 10 for chunk in chunks)
    assert "".join(chunk.text for chunk in chunks) == text


@pytest.mark.parametrize("mutation", ["gap", "truncated", "too_many"])
def test_rewrite_plan_fails_closed_on_coverage_and_capacity(mutation: str) -> None:
    text = "ONE\n12345678\n\nTWO\nabcdefgh\n"
    source = scenes(text, 0)
    maximum = 10
    if mutation == "gap":
        source = (
            source[0],
            ScreenplaySceneSource(source[1].id, source[1].start + 1, source[1].end),
        )
    elif mutation == "truncated":
        source = (
            source[0],
            ScreenplaySceneSource(source[1].id, source[1].start, source[1].end - 1),
        )
    else:
        maximum = 1

    with pytest.raises(AnalysisArtifactError) as error:
        plan_screenplay_rewrite(
            text, source, max_chunk_characters=10, max_chunks=maximum
        )

    assert error.value.code in {"artifact_integrity_failed", "analysis_resource_limit"}
