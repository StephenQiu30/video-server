from __future__ import annotations

from app.domain.analysis.enums import AnalysisValidationCode
from app.domain.analysis.errors import AnalysisValidationError
from app.domain.analysis.parse_helpers import ParseContext
from app.domain.analysis.result_models import (
    AnalysisChapter,
    AnalysisLimits,
    AnalysisResult,
    EvidenceStatement,
    MindMapNode,
)
from app.domain.analysis.result_validation import validate_analysis_result
from app.domain.analysis.transcript import Transcript


def parse_analysis_result(
    payload: object,
    transcript: Transcript,
    *,
    expected_schema_version: str,
    expected_language: str,
    limits: AnalysisLimits | None = None,
) -> AnalysisResult:
    context = ParseContext(limits or AnalysisLimits())
    root = context.mapping(
        payload,
        "result",
        {
            "schema_version",
            "language",
            "title",
            "summary",
            "key_points",
            "action_items",
            "chapters",
            "mind_map",
        },
    )
    schema_version = context.text(root["schema_version"], "schema_version", maximum=128)
    language = context.text(root["language"], "language", maximum=35)
    if schema_version != expected_schema_version or language != expected_language:
        raise AnalysisValidationError(
            AnalysisValidationCode.INVALID_SCHEMA,
            "schema version or output language does not match the job",
        )
    result = AnalysisResult(
        schema_version=schema_version,
        language=language,
        title=context.text(root["title"], "title"),
        summary=_statement(context, root["summary"], "summary"),
        key_points=tuple(
            _statement(context, item, f"key_points[{index}]")
            for index, item in enumerate(
                context.array(root["key_points"], "key_points", allow_empty=False)
            )
        ),
        action_items=tuple(
            _statement(context, item, f"action_items[{index}]")
            for index, item in enumerate(
                context.array(root["action_items"], "action_items", allow_empty=True)
            )
        ),
        chapters=tuple(
            _chapter(context, item, index)
            for index, item in enumerate(
                context.array(root["chapters"], "chapters", allow_empty=False)
            )
        ),
        mind_map=_node(context, root["mind_map"], depth=1),
    )
    validate_analysis_result(result, transcript, limits=context.limits)
    return result


def _evidence_ids(context: ParseContext, value: object, path: str) -> tuple[str, ...]:
    values = context.array(value, path, allow_empty=False)
    return tuple(
        context.text(item, f"{path}[{index}]", maximum=128)
        for index, item in enumerate(values)
    )


def _statement(context: ParseContext, value: object, path: str) -> EvidenceStatement:
    source = context.mapping(value, path, {"text", "evidence_segment_ids"})
    return EvidenceStatement(
        text=context.text(source["text"], f"{path}.text"),
        evidence_segment_ids=_evidence_ids(
            context, source["evidence_segment_ids"], f"{path}.evidence_segment_ids"
        ),
    )


def _chapter(context: ParseContext, value: object, index: int) -> AnalysisChapter:
    path = f"chapters[{index}]"
    source = context.mapping(
        value,
        path,
        {"title", "start_ms", "end_ms", "summary", "evidence_segment_ids"},
    )
    return AnalysisChapter(
        title=context.text(source["title"], f"{path}.title"),
        start_ms=context.integer(source["start_ms"], f"{path}.start_ms"),
        end_ms=context.integer(source["end_ms"], f"{path}.end_ms"),
        summary=context.text(source["summary"], f"{path}.summary"),
        evidence_segment_ids=_evidence_ids(
            context, source["evidence_segment_ids"], f"{path}.evidence_segment_ids"
        ),
    )


def _node(context: ParseContext, value: object, depth: int) -> MindMapNode:
    source = context.mapping(
        value,
        "mind_map node",
        {"id", "title", "evidence_segment_ids", "children"},
        {"summary", "start_ms"},
    )
    context.enter_node(source, depth)
    summary = source.get("summary")
    start_ms = source.get("start_ms")
    children = context.array(source["children"], "node.children", allow_empty=True)
    return MindMapNode(
        id=context.text(source["id"], "node.id", maximum=128),
        title=context.text(source["title"], "node.title"),
        summary=None if summary is None else context.text(summary, "node.summary"),
        start_ms=None
        if start_ms is None
        else context.integer(start_ms, "node.start_ms"),
        evidence_segment_ids=_evidence_ids(
            context, source["evidence_segment_ids"], "node.evidence_segment_ids"
        ),
        children=tuple(_node(context, child, depth + 1) for child in children),
    )
