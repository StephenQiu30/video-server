from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class StrictPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class EvidencePayload(StrictPayload):
    text: str
    evidence_segment_ids: list[str]


class ChapterPayload(StrictPayload):
    title: str
    start_ms: int
    end_ms: int
    summary: str
    evidence_segment_ids: list[str]


class MindMapNodePayload(StrictPayload):
    id: str
    title: str
    summary: str | None
    start_ms: int | None
    evidence_segment_ids: list[str]
    children: list[MindMapNodePayload]


class AnalysisPayload(StrictPayload):
    schema_version: str
    language: str
    title: str
    summary: EvidencePayload
    key_points: list[EvidencePayload]
    action_items: list[EvidencePayload]
    chapters: list[ChapterPayload]
    mind_map: MindMapNodePayload
