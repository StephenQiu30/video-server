from __future__ import annotations

import json
from dataclasses import asdict

from app.application.analysis import AnalysisJobSnapshot
from app.domain.analysis import (
    AnalysisValidationCode,
    AnalysisValidationError,
    ScreenplayAnalysisResult,
)

from .models import (
    AnalysisScreenplaySource,
    LocalScreenplayArtifact,
    ScreenplayAnalysisRequest,
    ScreenplaySceneSource,
)


def build_analysis_request(
    job: AnalysisJobSnapshot,
    source: AnalysisScreenplaySource,
    local: LocalScreenplayArtifact,
    text: str,
    scenes: tuple[ScreenplaySceneSource, ...],
) -> ScreenplayAnalysisRequest:
    return ScreenplayAnalysisRequest(
        screenplay=local.screenplay,
        workspace=local.workspace,
        screenplay_text=text,
        source_scene_ids=tuple(scene.id for scene in scenes),
        source_language=source.detected_language,
        output_language=job.output_language,
        skill_id=job.skill_id,
        skill_instructions=job.skill_instructions,
        custom_prompt=job.custom_prompt,
    )


def chunk_results_json(results: tuple[ScreenplayAnalysisResult, ...]) -> str:
    chunks: list[dict[str, object]] = []
    for result in results:
        document = asdict(result)
        document.pop("kind", None)
        chunks.append(document)
    return json.dumps({"chunks": chunks}, ensure_ascii=False, separators=(",", ":"))


def combined_analysis_payload(
    summary: object, results: tuple[ScreenplayAnalysisResult, ...]
) -> dict[str, object]:
    if not isinstance(summary, dict) or "scenes" in summary:
        raise AnalysisValidationError(
            AnalysisValidationCode.INVALID_SCHEMA,
            "screenplay synthesis result is invalid",
        )
    scenes = [
        {
            "id": scene.source_scene_id,
            "source_scene_id": scene.source_scene_id,
            "purpose": scene.purpose,
            "conflict": scene.conflict,
            "turn": scene.turn,
            "pacing": scene.pacing,
            "findings": list(scene.findings),
        }
        for result in results
        for scene in result.scenes
    ]
    return {**summary, "scenes": scenes}
