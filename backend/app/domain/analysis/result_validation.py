from __future__ import annotations

from app.domain.analysis.enums import AnalysisValidationCode
from app.domain.analysis.errors import AnalysisValidationError
from app.domain.analysis.result_models import (
    AnalysisLimits,
    AnalysisResult,
    EvidenceStatement,
    MindMapNode,
)
from app.domain.analysis.transcript import Transcript, TranscriptSegment


def validate_analysis_result(
    result: AnalysisResult,
    transcript: Transcript,
    *,
    limits: AnalysisLimits | None = None,
) -> None:
    limits = limits or AnalysisLimits()
    segments = {segment.id: segment for segment in transcript.segments}
    _refs(result.summary, segments)
    for statement in (*result.key_points, *result.action_items):
        _refs(statement, segments)

    previous_end = 0
    for chapter in result.chapters:
        if chapter.start_ms < previous_end or chapter.end_ms > transcript.duration_ms:
            _invalid_time("chapters must be monotonic and within the transcript")
        evidence = _segment_refs(chapter.evidence_segment_ids, segments)
        if any(
            item.start_ms < chapter.start_ms or item.end_ms > chapter.end_ms
            for item in evidence
        ):
            _invalid_time("chapter evidence falls outside its time range")
        previous_end = chapter.end_ms

    seen_ids: set[str] = set()
    seen_objects: set[int] = set()
    node_count = [0]
    _validate_node(
        result.mind_map,
        segments,
        seen_ids,
        seen_objects,
        node_count,
        depth=1,
        limits=limits,
    )


def _refs(
    statement: EvidenceStatement, segments: dict[str, TranscriptSegment]
) -> tuple[TranscriptSegment, ...]:
    return _segment_refs(statement.evidence_segment_ids, segments)


def _segment_refs(
    references: tuple[str, ...], segments: dict[str, TranscriptSegment]
) -> tuple[TranscriptSegment, ...]:
    try:
        return tuple(segments[segment_id] for segment_id in references)
    except KeyError as exc:
        raise AnalysisValidationError(
            AnalysisValidationCode.INVALID_EVIDENCE,
            f"unknown evidence segment id: {exc.args[0]}",
        ) from exc


def _validate_node(
    node: MindMapNode,
    segments: dict[str, TranscriptSegment],
    seen_ids: set[str],
    seen_objects: set[int],
    node_count: list[int],
    *,
    depth: int,
    limits: AnalysisLimits,
) -> None:
    identity = id(node)
    if identity in seen_objects or node.id in seen_ids:
        raise AnalysisValidationError(
            AnalysisValidationCode.DUPLICATE_IDENTIFIER,
            "mind map node ids and objects must be unique",
        )
    seen_objects.add(identity)
    seen_ids.add(node.id)
    node_count[0] += 1
    if depth > limits.max_mind_map_depth or node_count[0] > limits.max_mind_map_nodes:
        raise AnalysisValidationError(
            AnalysisValidationCode.LIMIT_EXCEEDED,
            "mind map exceeds depth or node limits",
        )
    evidence = _segment_refs(node.evidence_segment_ids, segments)
    if node.start_ms is not None and node.start_ms != min(
        item.start_ms for item in evidence
    ):
        _invalid_time("mind map start_ms must equal its earliest evidence")
    for child in node.children:
        _validate_node(
            child,
            segments,
            seen_ids,
            seen_objects,
            node_count,
            depth=depth + 1,
            limits=limits,
        )


def _invalid_time(detail: str) -> None:
    raise AnalysisValidationError(AnalysisValidationCode.INVALID_TIME_RANGE, detail)
