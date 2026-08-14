from dataclasses import replace

import pytest
from app.application.analysis import render_analysis_report_markdown
from app.domain.analysis import AnalysisValidationError, ScreenplayRewriteChunk
from tests.unit.domain.analysis.screenplay_factories import (
    screenplay_analysis_result,
    screenplay_rewrite_result,
)


def test_screenplay_analysis_rejects_unknown_evidence_scene() -> None:
    result = screenplay_analysis_result()
    invalid = replace(result.characters[0], evidence_scene_ids=("missing-scene",))

    with pytest.raises(AnalysisValidationError, match="unknown source scene"):
        replace(result, characters=(invalid,))


def test_screenplay_rewrite_requires_contiguous_unique_parts() -> None:
    result = screenplay_rewrite_result()
    duplicate = ScreenplayRewriteChunk(
        source_scene_id="scene-1",
        part_no=1,
        source_sha256="b" * 64,
        rewritten_text="Duplicate",
    )

    with pytest.raises(AnalysisValidationError, match="unique source scene"):
        replace(result, chunks=(*result.chunks, duplicate))


def test_screenplay_rewrite_rejects_interleaved_scene_chunks() -> None:
    result = screenplay_rewrite_result()
    scene_one_part_two = ScreenplayRewriteChunk(
        source_scene_id="scene-1",
        part_no=2,
        source_sha256="b" * 64,
        rewritten_text="Part two",
    )
    scene_two = ScreenplayRewriteChunk(
        source_scene_id="scene-2",
        part_no=1,
        source_sha256="c" * 64,
        rewritten_text="Scene two",
    )

    with pytest.raises(AnalysisValidationError, match="grouped"):
        replace(
            result,
            source_scene_count=2,
            output_scene_count=2,
            chunks=(result.chunks[0], scene_two, scene_one_part_two),
        )


def test_screenplay_reports_escape_untrusted_markdown_links_and_html() -> None:
    result = screenplay_rewrite_result(
        rewritten_text="![remote](https://invalid.example/x.png)\n<script>alert(1)</script>"
    )

    markdown = render_analysis_report_markdown(result)

    assert "![remote]" not in markdown
    assert "<script>" not in markdown
    assert "\\!\\[remote\\]" in markdown
    assert "&lt;script&gt;" in markdown
