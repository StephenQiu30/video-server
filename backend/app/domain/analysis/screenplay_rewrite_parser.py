from __future__ import annotations

from app.domain.analysis.enums import AnalysisValidationCode
from app.domain.analysis.errors import AnalysisValidationError
from app.domain.analysis.parse_helpers import ParseContext
from app.domain.analysis.result_models import AnalysisLimits
from app.domain.analysis.screenplay_rewrite_items import (
    ScreenplayGlossaryTerm,
    ScreenplayRewriteChunk,
    ScreenplayRewriteChunkOutput,
    ScreenplayRewriteGlossary,
)

_CATEGORIES = {"character", "location", "term", "title", "honorific", "other"}


def parse_screenplay_glossary(
    payload: object,
    *,
    expected_source_language: str,
    expected_target_language: str,
    limits: AnalysisLimits | None = None,
) -> ScreenplayRewriteGlossary:
    context = ParseContext(limits or AnalysisLimits())
    root = context.mapping(
        payload,
        "glossary",
        {"source_language", "target_language", "terms", "style_rules"},
    )
    source_language = context.text(
        root["source_language"], "source_language", maximum=35
    )
    target_language = context.text(
        root["target_language"], "target_language", maximum=35
    )
    if (
        source_language != expected_source_language
        or target_language != expected_target_language
    ):
        _invalid("screenplay glossary languages do not match the job")
    terms = tuple(
        _term(context, value, index)
        for index, value in enumerate(
            context.array(root["terms"], "terms", allow_empty=True)
        )
    )
    rules = tuple(
        context.text(value, f"style_rules[{index}]")
        for index, value in enumerate(
            context.array(root["style_rules"], "style_rules", allow_empty=False)
        )
    )
    return ScreenplayRewriteGlossary(
        source_language=source_language,
        target_language=target_language,
        terms=terms,
        style_rules=rules,
    )


def parse_screenplay_rewrite_chunk(
    payload: object,
    *,
    expected_scene_id: str,
    expected_part_no: int,
    expected_source_sha256: str,
    expected_target_language: str,
    limits: AnalysisLimits | None = None,
) -> ScreenplayRewriteChunkOutput:
    context = ParseContext(limits or AnalysisLimits())
    root = context.mapping(
        payload,
        "rewrite_chunk",
        {
            "source_scene_id",
            "part_no",
            "source_sha256",
            "target_language",
            "rewritten_text",
            "change_summary",
        },
    )
    scene_id = context.text(root["source_scene_id"], "source_scene_id", maximum=128)
    part_no = context.integer(root["part_no"], "part_no")
    source_sha256 = context.text(root["source_sha256"], "source_sha256", maximum=64)
    target_language = context.text(
        root["target_language"], "target_language", maximum=35
    )
    if (scene_id, part_no, source_sha256, target_language) != (
        expected_scene_id,
        expected_part_no,
        expected_source_sha256,
        expected_target_language,
    ):
        _invalid("screenplay rewrite chunk identity does not match the source")
    summaries = tuple(
        context.text(value, f"change_summary[{index}]")
        for index, value in enumerate(
            context.array(root["change_summary"], "change_summary", allow_empty=False)
        )
    )
    return ScreenplayRewriteChunkOutput(
        target_language=target_language,
        chunk=ScreenplayRewriteChunk(
            source_scene_id=scene_id,
            part_no=part_no,
            source_sha256=source_sha256,
            rewritten_text=context.preserved_text(
                root["rewritten_text"], "rewritten_text", maximum=200_000
            ),
        ),
        change_summary=summaries,
    )


def _term(context: ParseContext, value: object, index: int) -> ScreenplayGlossaryTerm:
    path = f"terms[{index}]"
    source = context.mapping(value, path, {"source", "target", "category"})
    category = context.text(source["category"], f"{path}.category", maximum=35)
    if category not in _CATEGORIES:
        _invalid("screenplay glossary category is invalid")
    return ScreenplayGlossaryTerm(
        source=context.text(source["source"], f"{path}.source"),
        target=context.text(source["target"], f"{path}.target"),
        category=category,
    )


def _invalid(detail: str) -> None:
    raise AnalysisValidationError(AnalysisValidationCode.INVALID_SCHEMA, detail)
