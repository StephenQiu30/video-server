from dataclasses import replace

import pytest
from app.services.analysis.report import render_analysis_report_markdown
from app.services.analysis.rules.errors import AnalysisValidationError
from app.services.analysis.rules.screenplay_rewrite_items import ScreenplayRewriteChunk
from tests.unit.services.analysis.rules.screenplay_factories import (
    screenplay_analysis_result,
    screenplay_rewrite_result,
)


def test_screenplay_analysis_rejects_duplicate_source_scene() -> None:
    result = screenplay_analysis_result()
    duplicate = replace(result.scenes[0], id="analysis-scene-2")

    with pytest.raises(
        AnalysisValidationError, match="source scene ids must be unique"
    ):
        replace(result, scenes=(*result.scenes, duplicate))


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
