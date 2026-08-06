"""Deterministic, transcript-free JSON document serialization."""

from typing import Any

from app.domain.analysis import (
    AnalysisChapter,
    AnalysisResult,
    EvidenceStatement,
    MindMapNode,
)


def analysis_result_document(result: AnalysisResult) -> dict[str, Any]:
    return {
        "schema_version": result.schema_version,
        "language": result.language,
        "title": result.title,
        "summary": _statement(result.summary),
        "key_points": [_statement(item) for item in result.key_points],
        "action_items": [_statement(item) for item in result.action_items],
        "chapters": [_chapter(item) for item in result.chapters],
        "mind_map": _node(result.mind_map),
    }


def _statement(value: EvidenceStatement) -> dict[str, Any]:
    return {
        "text": value.text,
        "evidence_segment_ids": list(value.evidence_segment_ids),
    }


def _chapter(value: AnalysisChapter) -> dict[str, Any]:
    return {
        "title": value.title,
        "start_ms": value.start_ms,
        "end_ms": value.end_ms,
        "summary": value.summary,
        "evidence_segment_ids": list(value.evidence_segment_ids),
    }


def _node(value: MindMapNode) -> dict[str, Any]:
    return {
        "id": value.id,
        "title": value.title,
        "summary": value.summary,
        "start_ms": value.start_ms,
        "evidence_segment_ids": list(value.evidence_segment_ids),
        "children": [_node(child) for child in value.children],
    }
