from __future__ import annotations

from pathlib import Path

from app.application.analysis import AnalysisJobSnapshot
from app.domain.analysis import (
    AnalysisValidationCode,
    AnalysisValidationError,
    ScreenplayRewriteChunkOutput,
    ScreenplayRewriteGlossary,
    ScreenplayRewriteResult,
)

from .errors import AnalysisArtifactError
from .models import LocalScreenplayArtifact
from .screenplay_rewrite_models import ScreenplayRewriteChunkRequest
from .screenplay_rewrite_plan import ScreenplayRewriteSourceChunk


def build_chunk_request(
    job: AnalysisJobSnapshot,
    local: LocalScreenplayArtifact,
    text: str,
    chunk: ScreenplayRewriteSourceChunk,
    glossary: ScreenplayRewriteGlossary,
    context: int,
) -> ScreenplayRewriteChunkRequest:
    return ScreenplayRewriteChunkRequest(
        screenplay=local.screenplay,
        workspace=local.workspace,
        source_text=chunk.text,
        context_before=text[max(0, chunk.start - context) : chunk.start],
        context_after=text[chunk.end : chunk.end + context],
        source_scene_id=chunk.source_scene_id,
        part_no=chunk.part_no,
        source_sha256=chunk.source_sha256,
        target_language=job.output_language,
        glossary=glossary,
        skill_id=job.skill_id,
        skill_instructions=job.skill_instructions,
        custom_prompt=job.custom_prompt,
    )


def build_rewrite_result(
    source_language: str,
    target_language: str,
    plan: tuple[ScreenplayRewriteSourceChunk, ...],
    glossary: ScreenplayRewriteGlossary,
    outputs: tuple[ScreenplayRewriteChunkOutput, ...],
) -> ScreenplayRewriteResult:
    expected = tuple(
        (item.source_scene_id, item.part_no, item.source_sha256) for item in plan
    )
    actual = tuple(
        (item.chunk.source_scene_id, item.chunk.part_no, item.chunk.source_sha256)
        for item in outputs
    )
    if actual != expected:
        raise AnalysisValidationError(
            AnalysisValidationCode.INVALID_EVIDENCE,
            "screenplay rewrite output does not cover the source plan",
        )
    _validate_glossary_usage(plan, glossary, outputs)
    summaries = tuple(
        dict.fromkeys(
            summary for output in outputs for summary in output.change_summary
        )
    )
    scene_count = len({chunk.source_scene_id for chunk in plan})
    return ScreenplayRewriteResult(
        source_language=source_language,
        target_language=target_language,
        source_scene_count=scene_count,
        output_scene_count=scene_count,
        glossary=glossary.terms,
        chunks=tuple(output.chunk for output in outputs),
        change_summary=summaries,
    )


def _validate_glossary_usage(
    plan: tuple[ScreenplayRewriteSourceChunk, ...],
    glossary: ScreenplayRewriteGlossary,
    outputs: tuple[ScreenplayRewriteChunkOutput, ...],
) -> None:
    source = "".join(chunk.text for chunk in plan).casefold()
    rewritten = "".join(output.chunk.rewritten_text for output in outputs).casefold()
    for term in glossary.terms:
        source_count = source.count(term.source.casefold())
        if source_count and rewritten.count(term.target.casefold()) < source_count:
            raise AnalysisValidationError(
                AnalysisValidationCode.INVALID_EVIDENCE,
                "screenplay rewrite output violates the validated glossary",
            )


def read_screenplay_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise AnalysisArtifactError("artifact_integrity_failed") from exc
