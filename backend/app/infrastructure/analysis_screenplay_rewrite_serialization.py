from app.domain.analysis import (
    AnalysisResultKind,
    ScreenplayGlossaryTerm,
    ScreenplayRewriteChunk,
    ScreenplayRewriteResult,
)
from app.infrastructure.analysis_storage_fields import (
    array,
    integer,
    mapping,
    string,
    strings,
)

_FIELDS = {
    "kind",
    "source_language",
    "target_language",
    "source_scene_count",
    "output_scene_count",
    "glossary",
    "chunks",
    "change_summary",
}


def screenplay_rewrite_from_document(document: object) -> ScreenplayRewriteResult:
    root = mapping(document, _FIELDS, "screenplay rewrite result")
    if root["kind"] != AnalysisResultKind.SCREENPLAY_REWRITE.value:
        raise ValueError("stored screenplay rewrite kind is invalid")
    return ScreenplayRewriteResult(
        source_language=string(root["source_language"], "source_language"),
        target_language=string(root["target_language"], "target_language"),
        source_scene_count=integer(root["source_scene_count"], "source_scene_count"),
        output_scene_count=integer(root["output_scene_count"], "output_scene_count"),
        glossary=tuple(
            _glossary_term(value) for value in array(root["glossary"], "glossary")
        ),
        chunks=tuple(
            _rewrite_chunk(value) for value in array(root["chunks"], "chunks")
        ),
        change_summary=strings(root["change_summary"], "change_summary"),
    )


def _glossary_term(value: object) -> ScreenplayGlossaryTerm:
    source = mapping(value, {"source", "target", "category"}, "glossary term")
    return ScreenplayGlossaryTerm(
        source=string(source["source"], "glossary.source"),
        target=string(source["target"], "glossary.target"),
        category=string(source["category"], "glossary.category"),
    )


def _rewrite_chunk(value: object) -> ScreenplayRewriteChunk:
    source = mapping(
        value,
        {"source_scene_id", "part_no", "source_sha256", "rewritten_text"},
        "rewrite chunk",
    )
    return ScreenplayRewriteChunk(
        source_scene_id=string(source["source_scene_id"], "chunk.source_scene_id"),
        part_no=integer(source["part_no"], "chunk.part_no"),
        source_sha256=string(source["source_sha256"], "chunk.source_sha256"),
        rewritten_text=string(source["rewritten_text"], "chunk.rewritten_text"),
    )
